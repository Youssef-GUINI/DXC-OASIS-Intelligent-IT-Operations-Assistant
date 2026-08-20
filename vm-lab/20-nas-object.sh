#!/usr/bin/env bash
#
# vm-lab/20-nas-object.sh
#
# Niveau 2 du laboratoire : ajoute au socle SAN/LVM les deux autres familles
# de stockage d'entreprise, et la cible de sauvegarde immuable.
#
#   NAS fichier      -> export NFS (NFSv4) et partage SMB (Samba)
#   Stockage objet   -> MinIO, compatible S3
#   Sauvegarde       -> dépôt restic hors-site sur MinIO, bucket en Object Lock
#                       COMPLIANCE : c'est le "1" immuable de la règle 3-2-1-1-0
#
# À lancer après 10-storage-lab.sh. Idempotent.
#
# Usage :  sudo bash 20-nas-object.sh
#
set -euo pipefail

VG_NAME=${VG_NAME:-vg_prod}
NAS_ROOT=${NAS_ROOT:-/srv/nas}
OBJECT_ROOT=${OBJECT_ROOT:-/srv/objectstore}
CONFIG_DIR=/etc/oasis-lab
HOSTONLY_NETWORK=${HOSTONLY_NETWORK:-192.168.56.0/24}
MINIO_PORT=${MINIO_PORT:-9000}
MINIO_CONSOLE_PORT=${MINIO_CONSOLE_PORT:-9001}
IMMUTABLE_BUCKET=${IMMUTABLE_BUCKET:-oasis-immutable}
RETENTION_DAYS=${RETENTION_DAYS:-7}

# Volumes NAS taillés dans le VG : ils apparaissent ainsi dans get_capacity au
# même titre que les LUN, avec leur propre taux de remplissage.
NAS_VOLUMES=(
    "lv_nas_nfs|1G|ext4|${NAS_ROOT}/nfs_prod"
    "lv_nas_smb|1G|ext4|${NAS_ROOT}/smb_finance"
)

if [[ $EUID -ne 0 ]]; then
    echo "Ce script doit être lancé avec sudo." >&2
    exit 1
fi

if ! vgs "$VG_NAME" >/dev/null 2>&1; then
    echo "Le volume group $VG_NAME n'existe pas : lance d'abord 10-storage-lab.sh." >&2
    exit 1
fi

step() { echo; echo "==> $*"; }

# ------------------------------------------------------- volumes des NAS
step "Volumes dédiés aux partages NAS"
free_gb=$(vgs --noheadings --nosuffix --units g -o vg_free "$VG_NAME" | tr -d ' ')
echo "  espace libre dans ${VG_NAME} : ${free_gb}G"

for entry in "${NAS_VOLUMES[@]}"; do
    IFS='|' read -r lv_name lv_size lv_fs mountpoint <<< "$entry"
    device="/dev/${VG_NAME}/${lv_name}"

    if ! lvs "$device" >/dev/null 2>&1; then
        lvcreate -y -L "$lv_size" -n "$lv_name" "$VG_NAME" >/dev/null
        echo "  LV créé  $lv_name ($lv_size)"
    fi
    blkid "$device" >/dev/null 2>&1 || mkfs.ext4 -q "$device"

    mkdir -p "$mountpoint"
    mountpoint -q "$mountpoint" || mount "$device" "$mountpoint"
    grep -qs "^${device} " /etc/fstab \
        || echo "${device} ${mountpoint} ${lv_fs} defaults,nofail,x-systemd.device-timeout=1 0 2" >> /etc/fstab
    echo "  monté    $mountpoint"
done

export DEBIAN_FRONTEND=noninteractive

# ------------------------------------------------------------------- NFS
step "Export NFS de ${NAS_ROOT}/nfs_prod vers ${HOSTONLY_NETWORK}"
apt-get install -y -qq nfs-kernel-server

# no_subtree_check : recommandé par exportfs dès que l'export n'est pas un
# système de fichiers entier. sync : pas d'acquittement avant écriture réelle.
export_line="${NAS_ROOT}/nfs_prod ${HOSTONLY_NETWORK}(rw,sync,no_subtree_check)"
if ! grep -qs "^${NAS_ROOT}/nfs_prod " /etc/exports; then
    echo "$export_line" >> /etc/exports
fi
chmod 777 "${NAS_ROOT}/nfs_prod"
exportfs -ra
systemctl enable --now nfs-server >/dev/null
exportfs -v | sed 's/^/  /'

# ------------------------------------------------------------------ Samba
step "Partage SMB finance"
apt-get install -y -qq samba

SMB_SHARE="${NAS_ROOT}/smb_finance"
SMB_USER=${SMB_USER:-oasislab}
SMB_CREDENTIALS="${CONFIG_DIR}/smb-credentials"

# Partage authentifié, et non invité : depuis Windows 11 24H2 la signature SMB
# est exigée par défaut côté client, or une session invitée ne peut pas être
# signée — un partage `guest ok = yes` est donc inaccessible depuis Windows,
# quelle que soit la configuration de Samba. C'est aussi la configuration
# réaliste : un partage NAS d'entreprise est toujours authentifié.
mkdir -p "$CONFIG_DIR"
id "$SMB_USER" >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin "$SMB_USER"
chown -R "${SMB_USER}:${SMB_USER}" "$SMB_SHARE"
chmod 770 "$SMB_SHARE"

# -s et non -f : un fichier vide signifie qu'une exécution précédente a été
# interrompue entre la création du fichier et son écriture. Le mot de passe
# posé alors est perdu — il faut en régénérer un, pas sauter l'étape.
if [[ ! -s $SMB_CREDENTIALS ]]; then
    smb_password=$(openssl rand -base64 18 | tr -d '/+=' | head -c 18)
    printf '%s\n%s\n' "$smb_password" "$smb_password" | smbpasswd -s -a "$SMB_USER" >/dev/null
    smbpasswd -e "$SMB_USER" >/dev/null
    cat > "$SMB_CREDENTIALS" <<CREDS
SMB_USER=${SMB_USER}
SMB_PASSWORD=${smb_password}
CREDS
    chmod 600 "$SMB_CREDENTIALS"
    echo "  compte ${SMB_USER} créé, mot de passe dans ${SMB_CREDENTIALS}"
fi

# La définition du partage vit dans son propre fichier : le script la gère
# entièrement sans réécrire smb.conf à chaque passage.
cat > /etc/samba/oasis-lab.conf <<SMB
[finance]
   comment = Partage NAS finance (laboratoire OASIS)
   path = ${SMB_SHARE}
   browseable = yes
   read only = no
   guest ok = no
   valid users = ${SMB_USER}
   force user = ${SMB_USER}
SMB

# Un arrêt brutal pendant une écriture laisse des octets NUL en tête de la
# ligne écrite (allocation différée d'ext4) : Samba ne reconnaît alors plus la
# directive, sans le moindre message d'erreur. On nettoie avant de relire.
if LC_ALL=C grep -q $'\000' /etc/samba/smb.conf 2>/dev/null; then
    tr -d '\000' < /etc/samba/smb.conf > /etc/samba/smb.conf.tmp
    mv /etc/samba/smb.conf.tmp /etc/samba/smb.conf
    echo "  octets NUL retirés de smb.conf (séquelle d'un arrêt brutal)"
fi

# Retire la version invitée écrite par un passage antérieur. On s'arrête à la
# section suivante : un `sed '/^\[finance\]/,$d'` couperait tout ce qui suit,
# y compris des sections ajoutées par ailleurs.
if grep -qs '^\[finance\]' /etc/samba/smb.conf; then
    awk '
        /^\[finance\]/ { skipping = 1; next }
        /^\[/          { skipping = 0 }
        !skipping      { print }
    ' /etc/samba/smb.conf > /etc/samba/smb.conf.tmp
    mv /etc/samba/smb.conf.tmp /etc/samba/smb.conf
fi

grep -qs '^include = /etc/samba/oasis-lab.conf' /etc/samba/smb.conf \
    || echo 'include = /etc/samba/oasis-lab.conf' >> /etc/samba/smb.conf
testparm -s >/dev/null 2>&1 || { echo "Configuration Samba invalide." >&2; exit 1; }
systemctl enable --now smbd >/dev/null
# La configuration vient peut-être de changer : smbd relit smb.conf au
# démarrage seulement.
systemctl restart smbd
systemctl is-active smbd | sed 's/^/  smbd : /'

# ----------------------------------------------------------------- MinIO
step "Stockage objet MinIO"

install_binary() {
    local url=$1 destination=$2
    [[ -x $destination ]] && return 0
    echo "  téléchargement $(basename "$destination")"
    if ! curl -fsSL --connect-timeout 15 "$url" -o "$destination"; then
        return 1
    fi
    chmod +x "$destination"
}

minio_ready=1
install_binary "https://dl.min.io/server/minio/release/linux-amd64/minio" /usr/local/bin/minio || minio_ready=0
install_binary "https://dl.min.io/client/mc/release/linux-amd64/mc" /usr/local/bin/mcli || minio_ready=0

if [[ $minio_ready -eq 0 ]]; then
    echo
    echo "  MinIO n'a pas pu être téléchargé (pas d'accès Internet depuis la VM ?)."
    echo "  NFS et SMB sont en place ; relance ce script quand la VM aura Internet."
    exit 0
fi

# Le client MinIO s'appelle mcli et non mc : sur Debian/Ubuntu, mc est déjà
# Midnight Commander.

id minio-user >/dev/null 2>&1 || useradd --system --shell /sbin/nologin minio-user
mkdir -p "$OBJECT_ROOT"
chown -R minio-user:minio-user "$OBJECT_ROOT"

if [[ ! -f /etc/default/minio ]]; then
    # Identifiants de service, générés localement et lisibles par root seul.
    root_password=$(openssl rand -base64 24 | tr -d '/+=' | head -c 24)
    cat > /etc/default/minio <<ENV
MINIO_ROOT_USER=oasisadmin
MINIO_ROOT_PASSWORD=${root_password}
MINIO_VOLUMES=${OBJECT_ROOT}
MINIO_OPTS="--address :${MINIO_PORT} --console-address :${MINIO_CONSOLE_PORT}"
ENV
    chmod 600 /etc/default/minio
    echo "  identifiants générés dans /etc/default/minio (lisible par root)"
fi

# systemd accepte une valeur non quotée contenant des espaces, pas bash :
# sans guillemets, sourcer ce fichier fait interpréter ":9000" comme une
# commande. Rattrape un fichier écrit par une version antérieure du script.
sed -i 's|^MINIO_OPTS=\(--address.*\)$|MINIO_OPTS="\1"|' /etc/default/minio

cat > /etc/systemd/system/minio.service <<'UNIT'
[Unit]
Description=MinIO object storage (laboratoire OASIS)
After=network-online.target
Wants=network-online.target

[Service]
User=minio-user
Group=minio-user
EnvironmentFile=/etc/default/minio
ExecStart=/usr/local/bin/minio server $MINIO_VOLUMES $MINIO_OPTS
Restart=always
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now minio >/dev/null

# Attendre que l'API réponde avant de créer les buckets.
for _ in $(seq 1 20); do
    curl -fsS "http://127.0.0.1:${MINIO_PORT}/minio/health/live" >/dev/null 2>&1 && break
    sleep 1
done
systemctl is-active minio | sed 's/^/  minio : /'

# Lecture ciblée plutôt que `source` : le fichier est destiné à systemd, sa
# syntaxe n'est pas garantie compatible avec bash.
read_env() { sed -n "s/^$1=//p" /etc/default/minio | tr -d '"' | head -1; }
MINIO_ROOT_USER=$(read_env MINIO_ROOT_USER)
MINIO_ROOT_PASSWORD=$(read_env MINIO_ROOT_PASSWORD)

mcli alias set oasis "http://127.0.0.1:${MINIO_PORT}" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null

step "Buckets, versioning et immuabilité"
if ! mcli ls "oasis/${IMMUTABLE_BUCKET}" >/dev/null 2>&1; then
    # --with-lock active le verrouillage d'objet, qui exige le versioning.
    # Il ne peut PAS être activé après coup : c'est un choix à la création.
    mcli mb --with-lock "oasis/${IMMUTABLE_BUCKET}" >/dev/null
    echo "  bucket ${IMMUTABLE_BUCKET} créé avec Object Lock"
fi

# COMPLIANCE : même le compte root ne peut pas supprimer l'objet avant la fin
# du délai. GOVERNANCE laisserait un administrateur passer outre — c'est
# précisément la différence qui protège d'un ransomware ayant volé un compte.
mcli retention set --default COMPLIANCE "${RETENTION_DAYS}d" "oasis/${IMMUTABLE_BUCKET}" >/dev/null
mcli retention info --default "oasis/${IMMUTABLE_BUCKET}" | sed 's/^/  /'

# ------------------------------------------- sauvegarde hors-site immuable
step "Job de sauvegarde hors-site vers le stockage objet"
PASSWORD_FILE="$CONFIG_DIR/restic-password"
if [[ ! -f $PASSWORD_FILE ]]; then
    echo "  $PASSWORD_FILE introuvable : lance d'abord 10-storage-lab.sh." >&2
    exit 1
fi

cat > "$CONFIG_DIR/backup-offsite.env" <<ENV
RESTIC_REPOSITORY=s3:http://127.0.0.1:${MINIO_PORT}/${IMMUTABLE_BUCKET}
RESTIC_PASSWORD_FILE=${PASSWORD_FILE}
AWS_ACCESS_KEY_ID=${MINIO_ROOT_USER}
AWS_SECRET_ACCESS_KEY=${MINIO_ROOT_PASSWORD}
ENV
chmod 600 "$CONFIG_DIR/backup-offsite.env"

set -a; . "$CONFIG_DIR/backup-offsite.env"; set +a
restic cat config >/dev/null 2>&1 || restic init >/dev/null

cat > /etc/systemd/system/backup-offsite.service <<UNIT
[Unit]
Description=Copie hors-site immuable vers le stockage objet
After=minio.service oasis-lab-storage.service
Requires=minio.service

[Service]
Type=oneshot
EnvironmentFile=${CONFIG_DIR}/backup-offsite.env
# Pas de forget --prune ici : les objets sont verrouillés jusqu'à l'expiration
# de la rétention, une purge échouerait. C'est le comportement attendu d'une
# cible immuable, pas un défaut de configuration.
ExecStart=/usr/bin/restic backup --tag offsite /srv/luns /srv/nas
UNIT

cat > /etc/systemd/system/backup-offsite.timer <<'UNIT'
[Unit]
Description=Copie hors-site immuable (planification)

[Timer]
OnCalendar=*-*-* 04:00:00
Persistent=true

[Install]
WantedBy=timers.target
UNIT

systemctl daemon-reload
systemctl enable --now backup-offsite.timer >/dev/null
echo "  backup-offsite.timer -> tous les jours à 04:00"

step "Première copie hors-site"
systemctl start backup-offsite.service
journalctl -u backup-offsite.service -n 4 --no-pager -o cat || true

# ------------------------------------------------------------------ bilan
step "Niveau 2 en place"
echo
echo "--- Volumes vus par get_capacity ---"
df -h -T | awk 'NR==1 || /\/srv\//'
echo
echo "--- Partages fichiers ---"
exportfs -v | sed 's/^/  NFS : /'
echo "  SMB : //192.168.56.10/finance (utilisateur ${SMB_USER}, mot de passe dans ${SMB_CREDENTIALS})"
echo
echo "--- Stockage objet ---"
mcli ls oasis | sed 's/^/  /'
mcli du "oasis/${IMMUTABLE_BUCKET}" | sed 's/^/  /'
echo
echo "--- Règle 3-2-1-1-0 couverte ---"
echo "  3 copies    : données de production + dépôt restic local + copie objet"
echo "  2 supports  : volumes LVM et stockage objet S3"
echo "  1 hors-site : bucket ${IMMUTABLE_BUCKET} (à héberger ailleurs en production)"
echo "  1 immuable  : Object Lock COMPLIANCE ${RETENTION_DAYS} jours"
echo "  0 erreur    : backup-restore-test.timer vérifie la restauration chaque semaine"
echo
echo "Console MinIO : http://192.168.56.10:${MINIO_CONSOLE_PORT}"
echo "Identifiants  : /etc/default/minio"

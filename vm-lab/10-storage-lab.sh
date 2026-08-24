#!/usr/bin/env bash
#
# vm-lab/10-storage-lab.sh
#
# Construit dans la VM l'infrastructure Storage & Backup que les tools MCP
# interrogent réellement. Rien n'est simulé côté application : ce script crée
# de vrais objets Linux, et les tools les lisent avec df / lvs / systemctl.
#
#   Baie de disques      -> 3 fichiers loopback (PV)
#   Pool de la baie      -> volume group vg_prod
#   LUN présenté au SI   -> logical volume formaté et monté sous /srv/luns/
#   Logiciel de backup   -> restic, piloté par des timers systemd backup-*
#   Appliance de dédup   -> dédup/compression natives de restic (restic stats)
#   Rétention            -> restic forget --keep-daily/--keep-weekly
#   Test de restauration -> unit backup-restore-test, hebdomadaire
#
# Idempotent : relançable sans casser l'existant.
#
# Usage :  sudo bash 10-storage-lab.sh
#
set -euo pipefail

# ---------------------------------------------------------------- paramètres
VG_NAME=${VG_NAME:-vg_prod}
LAB_ROOT=${LAB_ROOT:-/srv/lab}
DISK_DIR=$LAB_ROOT/disks
DISK_COUNT=${DISK_COUNT:-3}
DISK_SIZE_GB=${DISK_SIZE_GB:-5}
LUN_ROOT=${LUN_ROOT:-/srv/luns}
BACKUP_ROOT=${BACKUP_ROOT:-/srv/backup}
RESTORE_TEST_DIR=${RESTORE_TEST_DIR:-/srv/restore-test}
CONFIG_DIR=/etc/oasis-lab

# Utilisateur SSH utilisé par le backend (STORAGE_VM_USER du .env).
SSH_USER=${SSH_USER:-${SUDO_USER:-kaouthar}}

# LUN simulés : nom_lv|taille|système de fichiers|point de montage
# Total 10G sur un VG de 15G : les 5G restants servent aux snapshots LVM.
LUNS=(
    "lv_vmware_ds01|5G|ext4|${LUN_ROOT}/vmware_ds01"
    "lv_oracle_data|3G|xfs|${LUN_ROOT}/oracle_data"
    "lv_archives|2G|ext4|${LUN_ROOT}/archives"
)

if [[ $EUID -ne 0 ]]; then
    echo "Ce script doit être lancé avec sudo." >&2
    exit 1
fi

step() { echo; echo "==> $*"; }

# ------------------------------------------------------------------ paquets
step "Installation des paquets (lvm2, xfsprogs, restic)"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq lvm2 xfsprogs restic

# ------------------------------------------------- disques loopback (les PV)
step "Disques de la baie : ${DISK_COUNT} x ${DISK_SIZE_GB}G dans ${DISK_DIR}"
mkdir -p "$DISK_DIR"

needed_bytes=$((DISK_COUNT * DISK_SIZE_GB * 1024 * 1024 * 1024))
available_bytes=$(df -B1 --output=avail "$DISK_DIR" | tail -1)
if (( available_bytes < needed_bytes )); then
    echo "Espace insuffisant : il faut ~$((needed_bytes / 1024 / 1024 / 1024))G, il reste $((available_bytes / 1024 / 1024 / 1024))G." >&2
    echo "Réduis DISK_SIZE_GB ou DISK_COUNT, par exemple : sudo DISK_SIZE_GB=3 bash $0" >&2
    exit 1
fi

loop_devices=()
for index in $(seq 1 "$DISK_COUNT"); do
    image=$(printf '%s/disk%02d.img' "$DISK_DIR" "$index")
    if [[ ! -f $image ]]; then
        # Fichier creux : l'espace réel n'est consommé qu'à l'écriture.
        truncate -s "${DISK_SIZE_GB}G" "$image"
        echo "  créé   $image"
    else
        echo "  existe $image"
    fi

    device=$(losetup -j "$image" | cut -d: -f1)
    if [[ -z $device ]]; then
        device=$(losetup --find --show "$image")
        echo "  attaché $image -> $device"
    fi
    loop_devices+=("$device")
done

# ------------------------------------------------------------------- LVM
step "Volume group ${VG_NAME}"
for device in "${loop_devices[@]}"; do
    if ! pvs --noheadings -o pv_name 2>/dev/null | grep -qw "$device"; then
        pvcreate -y "$device" >/dev/null
        echo "  PV créé sur $device"
    fi
done

if vgs "$VG_NAME" >/dev/null 2>&1; then
    for device in "${loop_devices[@]}"; do
        if ! pvs --noheadings -o pv_name,vg_name | awk -v d="$device" '$1==d && $2!=""' | grep -q .; then
            vgextend "$VG_NAME" "$device" >/dev/null
            echo "  $device ajouté à $VG_NAME"
        fi
    done
else
    vgcreate "$VG_NAME" "${loop_devices[@]}" >/dev/null
    echo "  $VG_NAME créé"
fi

step "Création des LUN (logical volumes)"
mkdir -p "$LUN_ROOT"
for entry in "${LUNS[@]}"; do
    IFS='|' read -r lv_name lv_size lv_fs mountpoint <<< "$entry"
    device="/dev/${VG_NAME}/${lv_name}"

    if ! lvs "$device" >/dev/null 2>&1; then
        lvcreate -y -L "$lv_size" -n "$lv_name" "$VG_NAME" >/dev/null
        echo "  LV créé   $lv_name ($lv_size)"
    fi

    if ! blkid "$device" >/dev/null 2>&1; then
        case $lv_fs in
            xfs)  mkfs.xfs -q "$device" ;;
            ext4) mkfs.ext4 -q "$device" ;;
            *)    echo "Système de fichiers inconnu : $lv_fs" >&2; exit 1 ;;
        esac
        echo "  formaté   $lv_name en $lv_fs"
    fi

    mkdir -p "$mountpoint"
    if ! mountpoint -q "$mountpoint"; then
        mount "$device" "$mountpoint"
        echo "  monté     $mountpoint"
    fi

    # nofail : au boot les loopbacks n'existent pas encore, le service
    # oasis-lab-storage.service ci-dessous rattrape le montage.
    fstab_line="${device} ${mountpoint} ${lv_fs} defaults,nofail,x-systemd.device-timeout=1 0 2"
    if ! grep -qs "^${device} " /etc/fstab; then
        echo "$fstab_line" >> /etc/fstab
    fi
done

# ------------------------------------------------ données de démonstration
step "Données applicatives de départ"
seed_volume() {
    local directory=$1 megabytes=$2 label=$3
    mkdir -p "$directory"
    if [[ ! -f "$directory/.seeded" ]]; then
        # Données partiellement compressibles : la dédup restic donne un
        # taux réaliste, ni 1:1 ni artificiellement énorme.
        dd if=/dev/urandom of="$directory/${label}-data-01.bin" bs=1M count="$megabytes" status=none
        head -c $((megabytes * 512 * 1024)) /dev/zero > "$directory/${label}-data-02.bin"
        cp "$directory/${label}-data-01.bin" "$directory/${label}-data-01.copy.bin"
        date -Iseconds > "$directory/.seeded"
        echo "  $directory rempli (~$((megabytes * 2))M)"
    fi
}
seed_volume "${LUN_ROOT}/vmware_ds01" 700 vmdk
seed_volume "${LUN_ROOT}/oracle_data" 400 oradata
seed_volume "${LUN_ROOT}/archives"    200 archive

# ------------------------------------- réattachement automatique au reboot
step "Service de réattachement au démarrage"
cat > /usr/local/sbin/oasis-lab-attach <<'ATTACH'
#!/usr/bin/env bash
# Réattache les fichiers-disques du lab, active le VG et remonte les LUN.
set -euo pipefail
for image in /srv/lab/disks/*.img; do
    [[ -e $image ]] || continue
    if [[ -z $(losetup -j "$image" | cut -d: -f1) ]]; then
        losetup --find "$image"
    fi
done
vgchange -ay >/dev/null
mount -a

# Au démarrage, les volumes n'existent pas encore quand systemd tente les
# montages de fstab : nfs-server, ordonné après ces montages, échoue en
# "Dependency failed". Les partages sont maintenant montés, on le relance.
if systemctl is-enabled nfs-server >/dev/null 2>&1; then
    exportfs -ra || true
    systemctl restart nfs-server || true
fi
ATTACH
chmod 755 /usr/local/sbin/oasis-lab-attach

cat > /etc/systemd/system/oasis-lab-storage.service <<'UNIT'
[Unit]
Description=OASIS lab - attach loopback disks and mount LUNs
After=local-fs.target
Before=backup-daily.service backup-weekly.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/sbin/oasis-lab-attach

[Install]
WantedBy=multi-user.target
UNIT

# --------------------------------------------------------- dépôt de backup
step "Dépôt de sauvegarde restic (rôle de l'appliance de déduplication)"
mkdir -p "$CONFIG_DIR" "$BACKUP_ROOT" "$RESTORE_TEST_DIR"
PASSWORD_FILE="$CONFIG_DIR/restic-password"
if [[ ! -f $PASSWORD_FILE ]]; then
    openssl rand -base64 24 > "$PASSWORD_FILE"
    chmod 600 "$PASSWORD_FILE"
    echo "  mot de passe du dépôt généré dans $PASSWORD_FILE"
fi

RESTIC_REPO="${BACKUP_ROOT}/repo"
cat > "$CONFIG_DIR/backup.env" <<ENV
RESTIC_REPOSITORY=${RESTIC_REPO}
RESTIC_PASSWORD_FILE=${PASSWORD_FILE}
ENV
chmod 600 "$CONFIG_DIR/backup.env"

if [[ ! -f "${RESTIC_REPO}/config" ]]; then
    RESTIC_PASSWORD_FILE="$PASSWORD_FILE" restic init --repo "$RESTIC_REPO" >/dev/null
    echo "  dépôt initialisé dans $RESTIC_REPO"
fi

# ------------------------------------------------------- jobs de sauvegarde
step "Jobs de sauvegarde (timers systemd)"

# Un dépôt restic ne tolère qu'une opération exclusive à la fois, et les trois
# jobs ci-dessous partagent le même dépôt : forget --prune et check y prennent
# un verrou. Lancés dans la même seconde -- ce que produit une démonstration,
# ou le rattrapage des timers Persistent=true après un redémarrage -- le second
# meurt sur « repository is already locked », alors même que sa sauvegarde a
# réussi : seule la rétention a échoué, et le job passe en failed. flock les
# met en file d'attente au lieu de les laisser se percuter ; --verbose écrit
# l'attente (ou son expiration) dans le journal, pour que l'échec reste lisible
# si la file ne se vide jamais.
RESTIC_LOCK=/run/lock/oasis-restic-repo.lock
RESTIC_LOCK_WAIT=900

# Une unit systemd n'a ni HOME ni XDG_CACHE_HOME : restic renonce alors à son
# cache et prévient qu'« un prune sans cache peut être très lent ». Un chemin
# explicite lui en rend un.
RESTIC_CACHE_DIR_PATH=/var/cache/restic
install -d -m 700 "$RESTIC_CACHE_DIR_PATH"

# Le tool list_backups reconnaît un job à son nom : tout timer contenant
# "backup" apparaît dans l'application.
write_job() {
    local name=$1 description=$2 calendar=$3 command=$4
    cat > "/etc/systemd/system/${name}.service" <<UNIT
[Unit]
Description=${description}
After=oasis-lab-storage.service
Requires=oasis-lab-storage.service

[Service]
Type=oneshot
Environment=RESTIC_CACHE_DIR=${RESTIC_CACHE_DIR_PATH}
EnvironmentFile=${CONFIG_DIR}/backup.env
ExecStart=/usr/bin/flock --verbose --wait ${RESTIC_LOCK_WAIT} ${RESTIC_LOCK} /bin/bash -c '${command}'
UNIT

    cat > "/etc/systemd/system/${name}.timer" <<UNIT
[Unit]
Description=${description} (planification)

[Timer]
OnCalendar=${calendar}
Persistent=true

[Install]
WantedBy=timers.target
UNIT
    echo "  ${name}.timer -> ${calendar}"
}

# Fenêtre de tir nocturne, rétention 7 quotidiennes / 4 hebdomadaires / 6 mensuelles.
write_job "backup-daily" \
    "Sauvegarde quotidienne des LUN de production" \
    "*-*-* 02:30:00" \
    "restic backup --tag daily ${LUN_ROOT}/vmware_ds01 ${LUN_ROOT}/oracle_data && restic forget --tag daily --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune"

write_job "backup-weekly" \
    "Sauvegarde hebdomadaire complète (production + archives)" \
    "Sun *-*-* 03:30:00" \
    "restic backup --tag weekly ${LUN_ROOT} && restic forget --tag weekly --keep-weekly 8 --prune"

# Test de restauration : la tâche que tout ingénieur Backup doit prouver.
write_job "backup-restore-test" \
    "Test hebdomadaire de restauration et vérification d'intégrité" \
    "Mon *-*-* 04:30:00" \
    "rm -rf ${RESTORE_TEST_DIR}/* && restic restore latest --target ${RESTORE_TEST_DIR} && restic check --read-data-subset=5%"

systemctl daemon-reload
systemctl enable --now oasis-lab-storage.service >/dev/null 2>&1 || true
systemctl enable --now backup-daily.timer backup-weekly.timer backup-restore-test.timer >/dev/null

# Une première exécution donne aux tools un "dernier succès" à afficher :
# sans elle, systemctl show ne renvoie aucun horodatage.
step "Première sauvegarde (peut prendre une minute)"
systemctl start backup-daily.service
systemctl is-active backup-daily.service >/dev/null 2>&1 || true
journalctl -u backup-daily.service -n 3 --no-pager -o cat || true

# ------------------------------------------------------ droits pour le MCP
step "Droits sudo pour l'utilisateur SSH du backend (${SSH_USER})"

# Les tools exécutent lvcreate / lvconvert via sudo sur une session SSH sans
# terminal : sans NOPASSWD, sudo attend un mot de passe et la commande échoue.
#
# Les deux dernières règles servent à repair_backup_repository, qui dépose un
# drop-in systemd. Elles sont volontairement étroites : les arguments sont
# figés dans la règle, donc le compte ne peut écrire *que* le fichier
# 50-oasis-repair.conf d'un répertoire .d, et rien d'autre sous /etc. Le
# joker sudoers ne franchit pas les « / », ce qui interdit toute évasion par
# chemin relatif. Si DROP_IN_NAME change dans
# backend/app/mcp/storage/tools/repair.py, il faut le changer ici aussi.
SUDOERS_FILE=/etc/sudoers.d/oasis-storage
cat > "$SUDOERS_FILE" <<SUDOERS
# Généré par vm-lab/10-storage-lab.sh — actions Storage pilotées par OASIS.
${SSH_USER} ALL=(root) NOPASSWD: /usr/sbin/lvs, /usr/sbin/vgs, /usr/sbin/pvs, \\
    /usr/sbin/lvcreate, /usr/sbin/lvremove, /usr/sbin/lvextend, /usr/sbin/lvconvert, \\
    /usr/bin/systemctl, /usr/bin/restic, /usr/bin/journalctl, \\
    /usr/bin/install -d -m 755 /etc/systemd/system/*.d, \\
    /usr/bin/tee /etc/systemd/system/*.d/50-oasis-repair.conf
SUDOERS
chmod 440 "$SUDOERS_FILE"
if ! visudo -cf "$SUDOERS_FILE" >/dev/null; then
    rm -f "$SUDOERS_FILE"
    echo "Fichier sudoers invalide, annulé." >&2
    exit 1
fi

# lvs et systemctl start exigent root, mais les tools les appellent sans sudo.
# Ces deux enveloppes ajoutent le sudo à leur place : aucune modification du
# code Python n'est nécessaire.
cat > /usr/local/bin/lvs <<'WRAPPER'
#!/usr/bin/env bash
# Enveloppe posée par vm-lab/10-storage-lab.sh : lvs exige root (il ouvre
# /dev/mapper/control), et les tools MCP l'appellent sans sudo depuis une
# session SSH non privilégiée.
if [[ $(id -u) -eq 0 ]]; then
    exec /usr/sbin/lvs "$@"
fi
exec sudo -n /usr/sbin/lvs "$@"
WRAPPER
chmod 755 /usr/local/bin/lvs
echo "  enveloppe /usr/local/bin/lvs"

cat > /usr/local/bin/systemctl <<'WRAPPER'
#!/usr/bin/env bash
# Enveloppe posée par vm-lab/10-storage-lab.sh.
#
# Seules les actions qui modifient l'état du système exigent root : `start`,
# `stop`, `restart`… `show`, `list-timers` et consorts se lisent très bien
# sans privilège. Or sudo coûte environ 0,4 s par appel (PAM), contre 0,02 s
# en direct : tout passer par sudo rendait le dashboard lent de plusieurs
# secondes à chaque chargement, pour rien.
case ${1:-} in
    show|status|list-timers|list-units|list-unit-files|list-sockets|cat|\
    is-active|is-enabled|is-failed|show-environment|--version|--help)
        exec /usr/bin/systemctl "$@"
        ;;
esac

if [[ $(id -u) -eq 0 ]]; then
    exec /usr/bin/systemctl "$@"
fi
exec sudo -n /usr/bin/systemctl "$@"
WRAPPER
chmod 755 /usr/local/bin/systemctl
echo "  enveloppe /usr/local/bin/systemctl"

# ------------------------------------------------------------------ bilan
step "Infrastructure en place"
echo
echo "--- Volumes (ce que lit get_capacity) ---"
df -h -T | awk 'NR==1 || /\/srv\//'
echo
echo "--- LVM (ce que lit list_snapshots) ---"
lvs -o lv_name,vg_name,origin,lv_size,data_percent
echo
echo "--- Jobs de sauvegarde (ce que lit list_backups) ---"
systemctl list-timers --all --no-pager 'backup-*' | head -6
echo
echo "--- Taux de déduplication du dépôt ---"
set -a; . "$CONFIG_DIR/backup.env"; set +a
restic stats --mode raw-data 2>/dev/null | sed 's/^/  /' || echo "  (dépôt encore vide)"
echo
echo "Terminé. Injecte un incident de démonstration avec :"
echo "    sudo bash inject-incident.sh fill-lun"

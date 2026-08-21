#!/usr/bin/env bash
#
# vm-lab/inject-incident.sh
#
# Provoque de vrais incidents de stockage dans la VM, pour que l'application
# les détecte avec ses propres seuils (get_storage_health : 90 % / 95 % de
# remplissage, job en échec, dernier succès > 24 h) et propose une action
# corrective. Aucune donnée n'est injectée dans l'application : c'est bien
# l'état de la machine qui change.
#
# Usage :  sudo bash inject-incident.sh <scénario> [options]
#
# Scénarios :
#   fill-lun [mountpoint] [pourcentage]  Saturer un LUN (défaut : vmware_ds01 à 96 %)
#   fail-backup                          Créer un job de sauvegarde qui échoue
#   stale-backup                         Faire vieillir le dernier succès (avance l'horloge)
#   io-load [secondes]                   Générer de la charge disque mesurable
#   snapshot                             Créer un point de restauration LVM
#   snapshot-pressure                    Remplir un snapshot jusqu'à saturation
#   status                               Afficher ce que l'application doit voir
#   clean                                Tout remettre en état sain
#
set -euo pipefail

VG_NAME=${VG_NAME:-vg_prod}
LUN_ROOT=${LUN_ROOT:-/srv/luns}
DEFAULT_LUN=${LUN_ROOT}/vmware_ds01
FILLER_NAME=.oasis-incident-filler
CONFIG_DIR=/etc/oasis-lab

if [[ $EUID -ne 0 ]]; then
    echo "Ce script doit être lancé avec sudo." >&2
    exit 1
fi

scenario=${1:-status}
shift || true

# --------------------------------------------------------------- saturation
fill_lun() {
    local mountpoint=${1:-$DEFAULT_LUN} target=${2:-96}
    mountpoint -q "$mountpoint" || { echo "$mountpoint n'est pas un volume monté." >&2; exit 1; }

    local used_kb avail_kb usable_kb wanted_kb missing_kb
    used_kb=$(df -k --output=used "$mountpoint" | tail -1)
    avail_kb=$(df -k --output=avail "$mountpoint" | tail -1)

    # Le pourcentage affiché par df se calcule sur used+avail, et non sur la
    # taille totale : ext4 réserve 5 % des blocs à root, invisibles dans avail
    # mais accessibles à un fallocate lancé en root. Viser un pourcentage de la
    # taille totale sature donc le volume au lieu de l'amener au seuil voulu.
    usable_kb=$(( used_kb + avail_kb ))
    wanted_kb=$(( usable_kb * target / 100 ))
    missing_kb=$(( wanted_kb - used_kb ))

    if (( missing_kb <= 0 )); then
        echo "$mountpoint est déjà au-delà de ${target} %."
        return
    fi

    echo "==> Remplissage de $mountpoint jusqu'à ~${target} % ($(( missing_kb / 1024 )) Mo)"
    # fallocate réserve réellement les blocs : df le voit immédiatement.
    fallocate -l "${missing_kb}K" "${mountpoint}/${FILLER_NAME}" 2>/dev/null \
        || dd if=/dev/zero of="${mountpoint}/${FILLER_NAME}" bs=1M count=$(( missing_kb / 1024 )) status=none
    df -h "$mountpoint" | tail -1
    echo
    echo "L'application doit maintenant lever une alerte disk_capacity (critical)"
    echo "et proposer un lvextend. Correction manuelle possible :"
    echo "    sudo lvextend -r -L +1G /dev/${VG_NAME}/lv_vmware_ds01"
}

# ------------------------------------------------------- job en échec
fail_backup() {
    echo "==> Création d'un job de sauvegarde qui échoue (backup-app-critical)"
    # Dépôt volontairement inexistant : restic sort en erreur, systemd
    # enregistre ExecMainStatus != 0, que list_backups remonte en "failed".
    cat > /etc/systemd/system/backup-app-critical.service <<'UNIT'
[Unit]
Description=Critical application backup

[Service]
Type=oneshot
Environment=RESTIC_REPOSITORY=/srv/backup/repo-inexistant
Environment=RESTIC_PASSWORD=demo
ExecStart=/usr/bin/restic backup /srv/luns/oracle_data
UNIT

    cat > /etc/systemd/system/backup-app-critical.timer <<'UNIT'
[Unit]
Description=Critical application backup (schedule)

[Timer]
OnCalendar=*-*-* 01:00:00
Persistent=true

[Install]
WantedBy=timers.target
UNIT

    systemctl daemon-reload
    systemctl enable --now backup-app-critical.timer >/dev/null
    systemctl start backup-app-critical.service || true
    echo
    systemctl show backup-app-critical.service -p ExecMainStatus -p Result
    echo
    echo "L'application doit lever une alerte backup_failed (high) sur backup-app-critical."
}

# ------------------------------------------------- dernier succès trop vieux
stale_backup() {
    echo "==> Vieillissement du dernier succès de sauvegarde"
    echo
    echo "systemd horodate les exécutions : impossible d'antidater un succès."
    echo "Le seul moyen sans attendre 24 h est d'avancer l'horloge de la VM."
    echo "Cette VM est un laboratoire, l'opération est réversible (clean)."
    echo
    read -r -p "Avancer l'horloge de la VM de 26 heures ? [oui/non] " answer
    [[ $answer == "oui" ]] || { echo "Annulé."; return; }

    # Les timers doivent être arrêtés : avec Persistent=true, le saut d'horloge
    # déclencherait un rattrapage qui rafraîchirait le dernier succès.
    systemctl stop backup-daily.timer backup-weekly.timer 2>/dev/null || true
    timedatectl set-ntp false
    date -s "+26 hours" >/dev/null
    date
    echo
    echo "L'application doit lever une alerte backup_stale (medium)."
    echo "Remets l'heure ensuite avec : sudo bash inject-incident.sh clean"
}

# ---------------------------------------------------------- charge disque
io_load() {
    local seconds=${1:-45}
    echo "==> Charge disque sur $DEFAULT_LUN pendant ${seconds}s"
    (
        end=$(( $(date +%s) + seconds ))
        while (( $(date +%s) < end )); do
            dd if=/dev/urandom of="${DEFAULT_LUN}/.oasis-load.tmp" bs=1M count=64 oflag=direct status=none 2>/dev/null || true
            sync
        done
        rm -f "${DEFAULT_LUN}/.oasis-load.tmp"
    ) &
    echo "  PID $!"
    echo
    echo "Interroge get_disk_performance pendant ce temps : /proc/diskstats bouge"
    echo "réellement, le graphique Storage Performance se remplit."
}

# ---------------------------------------------------------------- snapshots
create_snapshot() {
    local origin=${1:-lv_vmware_ds01} size=${2:-1G}
    local name="snap_${origin#lv_}_$(date +%Y%m%d-%H%M%S)"
    echo "==> Snapshot LVM $name sur $origin"
    lvcreate --snapshot --size "$size" --name "$name" "/dev/${VG_NAME}/${origin}"
    echo
    lvs -o lv_name,origin,lv_size,data_percent "$VG_NAME"
    echo
    echo "L'application doit lister ce snapshot, et pouvoir restaurer avec"
    echo "lvconvert --merge (action destructive : confirmation exigée côté UI)."
}

snapshot_pressure() {
    echo "==> Saturation d'un snapshot"
    local snapshot
    snapshot=$(lvs --noheadings -o lv_name,origin "$VG_NAME" | awk '$2!=""{print $1; exit}')
    if [[ -z ${snapshot:-} ]]; then
        echo "Aucun snapshot existant, j'en crée un."
        create_snapshot
        snapshot=$(lvs --noheadings -o lv_name,origin "$VG_NAME" | awk '$2!=""{print $1; exit}')
    fi
    # Écrire dans le volume d'origine fait grossir la zone copy-on-write.
    dd if=/dev/urandom of="${DEFAULT_LUN}/.oasis-cow.bin" bs=1M count=600 status=none
    sync
    lvs -o lv_name,origin,lv_size,data_percent "$VG_NAME"
    echo
    echo "data_percent du snapshot $snapshot augmente : au-delà de 100 %, LVM"
    echo "l'invalide. C'est le risque réel qu'un ingénieur surveille."
}

# -------------------------------------------------------------------- bilan
show_status() {
    echo "--- Volumes ---"
    df -h -T | awk 'NR==1 || /\/srv\//'
    echo
    echo "--- LVM ---"
    lvs -o lv_name,vg_name,origin,lv_size,data_percent 2>/dev/null
    echo
    echo "--- Jobs de sauvegarde ---"
    systemctl list-timers --all --no-pager 'backup-*' 2>/dev/null | head -8
    echo
    echo "--- Derniers résultats ---"
    for unit in backup-daily backup-weekly backup-restore-test backup-app-critical; do
        if systemctl list-unit-files "${unit}.service" >/dev/null 2>&1; then
            printf '%-22s %s\n' "$unit" "$(systemctl show "${unit}.service" -p Result --value 2>/dev/null)"
        fi
    done
    echo
    echo "--- Horloge ---"
    timedatectl | sed -n '1,3p'
}

# -------------------------------------------------------------- remise à zéro
clean_all() {
    echo "==> Suppression des fichiers de remplissage"
    find "$LUN_ROOT" -maxdepth 2 -name "$FILLER_NAME" -delete -print
    find "$LUN_ROOT" -maxdepth 2 -name '.oasis-*.bin' -delete -print
    find "$LUN_ROOT" -maxdepth 2 -name '.oasis-load.tmp' -delete -print

    echo "==> Suppression du job en échec"
    if [[ -f /etc/systemd/system/backup-app-critical.service ]]; then
        systemctl disable --now backup-app-critical.timer >/dev/null 2>&1 || true
        rm -f /etc/systemd/system/backup-app-critical.{service,timer}
        systemctl daemon-reload
    fi

    echo "==> Suppression des snapshots de démonstration"
    while read -r snapshot; do
        [[ -n $snapshot ]] || continue
        lvremove -y "/dev/${VG_NAME}/${snapshot}" >/dev/null && echo "  $snapshot supprimé"
    done < <(lvs --noheadings -o lv_name,origin "$VG_NAME" 2>/dev/null | awk '$2!=""{print $1}')

    echo "==> Remise à l'heure et redémarrage des timers"
    timedatectl set-ntp true || true
    systemctl start backup-daily.timer backup-weekly.timer 2>/dev/null || true
    sleep 2
    timedatectl | sed -n '1,3p'

    echo
    echo "==> État final"
    show_status
}

case $scenario in
    fill-lun)          fill_lun "$@" ;;
    fail-backup)       fail_backup ;;
    stale-backup)      stale_backup ;;
    io-load)           io_load "$@" ;;
    snapshot)          create_snapshot "$@" ;;
    snapshot-pressure) snapshot_pressure ;;
    status)            show_status ;;
    clean)             clean_all ;;
    *)
        sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'
        exit 1
        ;;
esac

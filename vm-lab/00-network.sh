#!/usr/bin/env bash
#
# vm-lab/00-network.sh
#
# Rend la VM joignable depuis Windows sur l'IP attendue par le backend
# (STORAGE_VM_HOST du .env), de façon persistante au redémarrage.
#
# Le problème corrigé ici : l'interface host-only (enp0s8) n'a aucune
# configuration netplan, donc elle reste DOWN à chaque boot et le backend
# échoue avec "Could not reach 192.168.56.10".
#
# Usage :  sudo bash 00-network.sh [IP] [INTERFACE]
#
set -euo pipefail

LAB_IP=${1:-192.168.56.10}
LAB_IFACE=${2:-enp0s8}
NETPLAN_FILE=/etc/netplan/60-oasis-hostonly.yaml

if [[ $EUID -ne 0 ]]; then
    echo "Ce script doit être lancé avec sudo." >&2
    exit 1
fi

if ! ip link show "$LAB_IFACE" >/dev/null 2>&1; then
    echo "Interface $LAB_IFACE introuvable. Interfaces disponibles :" >&2
    ip -brief link >&2
    echo "Vérifie qu'un adaptateur host-only est bien attaché à la VM (VirtualBox > Configuration > Réseau > Adaptateur 2)." >&2
    exit 1
fi

echo "==> Configuration netplan de $LAB_IFACE en $LAB_IP/24"
cat > "$NETPLAN_FILE" <<YAML
# Généré par vm-lab/00-network.sh — interface host-only vers le poste Windows.
network:
  version: 2
  ethernets:
    ${LAB_IFACE}:
      dhcp4: false
      addresses: [${LAB_IP}/24]
YAML
# netplan refuse d'appliquer un fichier lisible par tous.
chmod 600 "$NETPLAN_FILE"
netplan apply

echo "==> Activation de sshd"
if ! command -v sshd >/dev/null 2>&1; then
    apt-get update -qq
    apt-get install -y -qq openssh-server
fi
systemctl enable --now ssh

echo
echo "==> Résultat"
ip -brief addr show "$LAB_IFACE"
systemctl is-active ssh | sed 's/^/sshd: /'
echo
echo "Teste depuis Windows :"
echo "    ssh -i C:\\Users\\<toi>\\.ssh\\oasis_storage_vm_key $(logname 2>/dev/null || echo "$SUDO_USER")@${LAB_IP} hostname"

# Laboratoire Storage & Backup

Ces scripts construisent, dans une VM Ubuntu, l'infrastructure que les tools MCP
du persona Storage interrogent réellement.

Le principe est simple : **l'application ne simule rien**. Elle exécute `df`,
`lvs`, `systemctl` et lit `/proc/diskstats` sur une vraie machine, par SSH. Pour
que ses réponses soient riches, c'est donc la machine qu'il faut équiper — pas le
code. Ces scripts créent les objets Linux correspondants, et les rendent
reproductibles : l'infrastructure de démonstration se rejoue en une commande sur
une VM neuve.

## Ce qui est simulé, et par quoi

| Composant d'entreprise | Équivalent dans la VM |
|---|---|
| Disques d'une baie SAN | Fichiers loopback creux (`truncate` + `losetup`) déclarés en PV |
| Pool de la baie | Volume group `vg_prod` |
| LUN présenté à un hyperviseur | Logical volume formaté et monté sous `/srv/luns/` |
| Volume NFS d'un NAS | `nfs-kernel-server`, export `/srv/nas/nfs_prod` |
| Partage SMB d'un NAS | Samba, partage `finance` authentifié |
| Stockage objet S3 | MinIO |
| Logiciel de sauvegarde (Veeam, Commvault) | restic, piloté par des timers systemd |
| Appliance de déduplication | Déduplication et compression natives de restic |
| Cible Cloud hors-site | Dépôt restic sur MinIO |
| Sauvegarde immuable anti-ransomware | Object Lock MinIO en mode COMPLIANCE |
| Snapshot de baie et restauration | `lvcreate --snapshot`, `lvconvert --merge` |

### Ce qui n'est pas simulable — à assumer dans le rapport

- **Fibre Channel et zonage** : aucune émulation FC n'existe. L'équivalent
  honnête est iSCSI, où les ACL `targetcli` jouent le rôle du masquage de LUN.
  Non couvert par ces scripts.
- **Robots de bandes LTO** : `mhvtl` émule une bibliothèque virtuelle mais exige
  la compilation d'un module noyau. Hors de proportion pour une maquette.
- **Microcodes de baie** : il n'y a pas de firmware à mettre à jour sur une VM.
  L'approximation acceptable côté MCO est le suivi des paquets
  (`apt list --upgradable`) et l'expiration des certificats.

## Prérequis

- VM Ubuntu Server 24.04, 2 vCPU, 4 Go de RAM, **~15 Go libres** sur `/`
- Deux interfaces réseau : NAT (accès Internet, pour `apt` et le téléchargement
  de MinIO) et **host-only** (accès depuis le poste de travail)
- Une clé SSH du poste déposée dans `~/.ssh/authorized_keys` de la VM

## Installation

Copier les scripts dans la VM, puis les lancer dans l'ordre :

```bash
scp -i ~/.ssh/oasis_storage_vm_key vm-lab/*.sh <user>@<ip>:~/vm-lab/
```

```bash
sudo bash ~/vm-lab/00-network.sh      # IP fixe host-only + sshd
sudo bash ~/vm-lab/10-storage-lab.sh  # LVM, LUN, restic, timers  (~5 min)
sudo bash ~/vm-lab/20-nas-object.sh   # NFS, SMB, MinIO, immuabilité
```

Les trois scripts sont **idempotents** : les relancer ne recrée rien d'existant.

Renseigner ensuite `backend/.env` :

```
STORAGE_VM_HOST=192.168.56.10
STORAGE_VM_PORT=22
STORAGE_VM_USER=<user>
STORAGE_VM_SSH_KEY_PATH=C:\Users\<toi>\.ssh\oasis_storage_vm_key
```

## Ce que chaque script crée

### `00-network.sh`

Écrit `/etc/netplan/60-oasis-hostonly.yaml` pour donner une IP fixe à
l'interface host-only, et active `sshd`. Sans ce fichier, l'interface reste
`DOWN` à chaque démarrage et le backend échoue sur `Could not reach <ip>`.

### `10-storage-lab.sh`

| Objet | Détail |
|---|---|
| Disques | 3 fichiers creux de 5 Go dans `/srv/lab/disks` |
| Volume group | `vg_prod`, ~15 Go, dont ~5 Go laissés libres pour les snapshots |
| LUN | `lv_vmware_ds01` (5 Go, ext4), `lv_oracle_data` (3 Go, **xfs**), `lv_archives` (2 Go, ext4) |
| Points de montage | `/srv/luns/vmware_ds01`, `/srv/luns/oracle_data`, `/srv/luns/archives` |
| Dépôt de sauvegarde | restic dans `/srv/backup/repo`, mot de passe dans `/etc/oasis-lab/restic-password` |
| Jobs | `backup-daily` (02:30), `backup-weekly` (dim. 03:30), `backup-restore-test` (lun. 04:30) |
| Rétention | `restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune` |
| Persistance | `oasis-lab-storage.service` réattache les loopbacks et remonte les volumes au démarrage |

Deux points méritent l'attention :

- **Droits sudo.** Les tools exécutent `sudo lvcreate` et `sudo lvconvert` sur
  une session SSH sans terminal. Sans règle `NOPASSWD`, `sudo` attend un mot de
  passe que personne ne peut saisir, et la commande échoue. Le script installe
  `/etc/sudoers.d/oasis-storage`, limité aux binaires nécessaires.
- **Enveloppes `lvs` et `systemctl`.** Ces deux commandes exigent root, mais les
  tools les appellent sans `sudo`. Deux enveloppes dans `/usr/local/bin`
  ajoutent le `sudo` à leur place, ce qui évite de modifier le code Python.
  Conséquence en ligne de commande : `sudo lvs` échoue (la règle sudoers vise
  `/usr/sbin/lvs`, pas l'enveloppe) — utiliser `sudo /usr/sbin/lvs`.

### `20-nas-object.sh`

| Objet | Détail |
|---|---|
| Volumes NAS | `lv_nas_nfs` et `lv_nas_smb` (1 Go chacun) |
| NFS | export de `/srv/nas/nfs_prod` vers le réseau host-only |
| SMB | partage `finance`, utilisateur `oasislab`, mot de passe dans `/etc/oasis-lab/smb-credentials` |
| MinIO | service systemd, API `:9000`, console `:9001`, identifiants dans `/etc/default/minio` |
| Immuabilité | bucket `oasis-immutable` en Object Lock, rétention **COMPLIANCE 7 jours** |
| Hors-site | dépôt restic sur S3 et job `backup-offsite` (04:00) |

**COMPLIANCE et non GOVERNANCE** : en mode GOVERNANCE, un administrateur peut
lever le verrou — c'est précisément ce que ferait un ransomware ayant volé un
compte privilégié. En COMPLIANCE, même root ne peut pas supprimer l'objet avant
l'échéance.

**Pas de `restic forget --prune` sur le job hors-site** : sur un bucket
verrouillé, une purge échoue par construction. C'est le comportement attendu
d'une cible immuable, pas une erreur de configuration.

## Ce que lit l'application

| Tool MCP | Commande exécutée sur la VM |
|---|---|
| `get_capacity` | `df -T -B1 -P` |
| `list_backups` | `systemctl list-timers` puis `systemctl show --timestamp=unix` |
| `list_snapshots` | `lvs --noheadings -o lv_name,vg_name,origin,…` |
| `create_snapshot` | `sudo lvcreate --snapshot --size <n>G` |
| `restore_from_backup` | `sudo lvconvert --merge <snapshot>` |
| `sample_disk_performance` | deux lectures de `/proc/diskstats` espacées de 2 s |
| `get_storage_health` | agrège les deux premiers, seuils 90 % / 95 % / 24 h |

Un timer est reconnu comme job de sauvegarde si son nom contient `backup`,
`restic`, `borg`… Nommer un timer `backup-*.timer` suffit donc à le faire
apparaître dans l'application — à condition qu'il vienne de l'administrateur et
non d'un paquet de la distribution.

## Scénarios d'incident

```bash
sudo bash ~/vm-lab/inject-incident.sh <scénario>
```

| Scénario | Effet | Réaction attendue |
|---|---|---|
| `fill-lun [point de montage] [%]` | Sature un LUN à 96 % | alerte `disk_capacity` **critical** |
| `fail-backup` | Crée un job pointant vers un dépôt inexistant | alerte `backup_failed` **high** |
| `stale-backup` | Avance l'horloge de 26 h (réversible) | alerte `backup_stale` **medium** |
| `io-load [secondes]` | Charge disque réelle | `/proc/diskstats` bouge |
| `snapshot` | Crée un point de restauration LVM | snapshot listé |
| `snapshot-pressure` | Fait grossir la zone copy-on-write | `data_percent` augmente |
| `status` | Affiche l'état vu par l'application | — |
| `clean` | Remet tout en état sain | `healthy` |

Chaque incident a une remédiation réelle que l'agent peut proposer puis
exécuter : `lvextend -r -L +1G`, `systemctl start <job>`, `lvconvert --merge`,
`restic forget --prune`.

Exemple validé de bout en bout :

| Étape | Volume | `get_storage_health` |
|---|---|---|
| Départ | 4,8 Go — 38 % | `healthy` |
| `fill-lun` | 4,8 Go — 100 % | `critical` |
| `lvextend -r -L +1G` | 5,8 Go — 85 % | `healthy` |

`resize2fs` agrandit le système de fichiers **à chaud**, volume monté : la
saturation est résolue par une extension de capacité, sans rien supprimer.

## Pièges rencontrés

Ces points ont tous coûté du temps au moins une fois. Ils sont corrigés dans les
scripts, mais restent bons à connaître.

- **`sudo` sans mot de passe.** Une session SSH non interactive ne peut pas
  répondre à une invite de mot de passe : sans la règle sudoers, toute action
  d'écriture du persona échoue silencieusement.
- **`nfs-server` en échec au démarrage.** Le service est ordonné après les
  montages `fstab` des volumes qu'il exporte, or les disques loopback ne sont
  rattachés qu'ensuite. Le script de rattachement relance donc `exportfs -ra` et
  `nfs-server` une fois les volumes montés.
- **Partage SMB invité inaccessible depuis Windows 11 24H2.** La signature SMB
  y est exigée par défaut côté client, et une session invitée ne peut pas être
  signée : Windows refuse avant même de parler à Samba. D'où le partage
  authentifié.
- **Disposition du clavier.** La VM est en clavier US ; sur un clavier AZERTY,
  la console VirtualBox et une session SSH n'envoient pas les mêmes caractères.
  Un mot de passe défini dans la console ne fonctionne donc pas en SSH. Pour
  aligner les deux : `sudo localectl set-keymap fr` **puis** `passwd`, dans cet
  ordre.
- **Un snapshot bloque l'extension de son volume d'origine.** Avec les snapshots
  LVM classiques, `lvextend` refuse tant qu'un snapshot est attaché à un volume
  actif. Il faut supprimer le snapshot d'abord. La contrainte disparaît avec le
  thin provisioning.
- **Arrêt brutal de la VM.** L'allocation différée d'ext4 peut laisser des
  octets NUL en tête d'un fichier écrit juste avant la coupure. Samba, par
  exemple, ignore alors la ligne sans le moindre message d'erreur. En cas de
  comportement inexplicable après un arrêt brutal :
  `tr -dc '\000' < <fichier> | wc -c`.

## Remise à zéro

```bash
sudo bash ~/vm-lab/inject-incident.sh clean   # incidents seulement
```

Pour tout démonter, y compris les volumes :

```bash
sudo umount /srv/luns/* /srv/nas/*
sudo vgremove -y vg_prod && sudo losetup -D
sudo rm -rf /srv/lab /srv/luns /srv/nas /srv/backup
```

Penser à retirer les lignes correspondantes de `/etc/fstab`.

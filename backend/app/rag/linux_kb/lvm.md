# Gestion des Volumes LVM

## Architecture LVM

LVM (Logical Volume Manager) ajoute une couche d'abstraction entre le disque physique et le systeme de fichiers.

- PV (Physical Volume) : disque physique ou partition
- VG (Volume Group) : regroupement de PV
- LV (Logical Volume) : volume logique utilisable par le systeme de fichiers

## Commandes de base

Afficher les volumes physiques :

    pvs

Afficher les groupes de volumes :

    vgs

Afficher les volumes logiques :

    lvs

Detail complet :

    pvdisplay
    vgdisplay
    lvdisplay

## Extension d'un volume logique

Si le VG a de l'espace libre, etendre le LV est immediat :

    sudo lvextend -L +10G /dev/vg_data/lv_app
    sudo resize2fs /dev/vg_data/lv_app

Pour ext4, `resize2fs` permet d'agrandir a chaud sans demontage.

Pour XFS, utilisez `xfs_growfs` a la place :

    sudo xfs_growfs /mnt/app

## Creation d'un snapshot

Un snapshot LVM capture l'etat d'un LV a un instant T. Utile pour les backups coherents.

    sudo lvcreate -L 5G -s -n lv_app_snap /dev/vg_data/lv_app

Le snapshot doit avoir une taille suffisante pour stocker les modifications pendant sa duree de vie.

## Suppression d'un snapshot

    sudo lvremove /dev/vg_data/lv_app_snap

## Panne courante : VG plein

Si `lvextend` echoue avec "Insufficient free space", verifiez l'espace disponible dans le VG :

    vgs

Solutions : ajouter un nouveau PV au VG ou supprimer des LV inutilises.

## Actions correctives

1. Verifier l'etat avec `pvs`, `vgs`, `lvs`
2. Etendre le LV si besoin avec `lvextend` + `resize2fs`
3. Creer un snapshot avant toute operation risquee
4. Si un PV est defectueux : le retirer du VG avec `pvmove` puis `vgreduce`
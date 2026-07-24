# Gestion des Systemes de Fichiers Linux

## Types de systemes de fichiers courants

ext4 : systeme de fichiers par defaut sur la plupart des distributions Linux. Stable, journalise, supporte les fichiers jusqu'a 16 To.

XFS : optimise pour les gros fichiers et les charges paralleles. Utilise par defaut sur RHEL/CentOS. Ne peut pas etre reduit (shrink).

Btrfs : systeme de fichiers moderne avec snapshots, compression et checksums natifs. Plus complexe a administrer.

## Verification et reparation

Pour verifier un systeme de fichiers ext4 :

    sudo fsck -n /dev/sda1

L'option `-n` effectue une verification en lecture seule sans reparer. Pour reparer automatiquement :

    sudo fsck -y /dev/sda1

Important : ne jamais executer fsck sur un systeme de fichiers monte. Demontez-le d'abord :

    sudo umount /dev/sda1

## Superblock corrompu

Si fsck rapporte un superblock invalide, utilisez un superblock de backup :

    sudo dumpe2fs /dev/sda1 | grep -i superblock
    sudo fsck -b 32768 /dev/sda1

## Montage et fstab

Le fichier `/etc/fstab` definit les partitions a monter au demarrage. Une erreur dans ce fichier peut empecher le boot.

Pour tester une ligne fstab sans rebooter :

    sudo mount -a

Pour monter une partition specifique :

    sudo mount /dev/sdb1 /mnt/data

## Inodes

Un systeme de fichiers peut etre plein meme avec de l'espace disponible si tous les inodes sont utilises. Verifiez avec :

    df -i

Les inodes sont epuises par un grand nombre de petits fichiers (ex: cache mail, sessions PHP).

## Actions correctives

1. Verifier le type de systeme de fichiers avec `lsblk -f` ou `df -T`
2. Reparer avec fsck si des erreurs sont detectees
3. Corriger fstab si un point de montage est invalide
4. Liberer des inodes en supprimant les petits fichiers inutiles
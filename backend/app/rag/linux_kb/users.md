# Gestion des Utilisateurs et Groupes Linux

## Commandes de base

Ajouter un utilisateur :

    sudo useradd -m -s /bin/bash alice
    sudo passwd alice

Supprimer un utilisateur :

    sudo userdel -r alice

Modifier un utilisateur :

    sudo usermod -aG sudo alice

Lister les utilisateurs :

    cat /etc/passwd

## Groupes

Ajouter un groupe :

    sudo groupadd developers

Ajouter un utilisateur a un groupe :

    sudo usermod -aG developers alice

Lister les groupes d'un utilisateur :

    groups alice

## Fichiers systeme

/etc/passwd : liste des utilisateurs (UID, GID, shell, home)

/etc/shadow : mots de passes hashes (accessible uniquement en root)

/etc/group : liste des groupes

/etc/sudoers : configuration sudo (editer avec `visudo`)

## Sudo

Accorder les privileges sudo a un utilisateur :

    sudo usermod -aG sudo alice

Ou editer sudoers :

    sudo visudo

    alice ALL=(ALL:ALL) ALL

## Compte verrouille

Verrouiller un compte :

    sudo passwd -l alice

Deverrouiller :

    sudo passwd -u alice

Verifier si un compte est verrouille :

    sudo passwd -S alice

## Actions correctives

1. Verifier l'existence de l'utilisateur : `id alice`
2. Verifier les groupes : `groups alice`
3. Verifier les logs de connexion : `last` ou `lastlog`
4. Verifier les processus de l'utilisateur : `ps -u alice`
5. Pour un utilisateur qui ne peut pas se connecter : verifier le shell dans /etc/passwd et les permissions du home
6. Toujours utiliser `visudo` pour editer /etc/sudoers (validation de syntaxe integree)
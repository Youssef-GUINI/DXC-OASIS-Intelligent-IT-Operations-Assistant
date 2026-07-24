# Gestion des Permissions Linux

## Modele de permissions POSIX

Chaque fichier/dossier a 3 niveaux de permissions :
- u (user/proprietaire)
- g (group)
- o (others)

Chaque niveau a 3 droits :
- r (read / 4)
- w (write / 2)
- x (execute / 1)

## Commandes de base

Afficher les permissions :

    ls -l

Modifier les permissions :

    chmod 644 fichier.txt
    chmod 755 repertoire/
    chmod u+x script.sh

Modifier le proprietaire :

    sudo chown user:group fichier.txt

Modifier recursivement :

    sudo chown -R user:group /chemin/

## Permissions speciales

SUID (4) : execute avec les privileges du proprietaire

    chmod u+s /usr/bin/passwd

SGID (2) : execute avec les privileges du groupe

    chmod g+s /repertoire_partage

Sticky bit (1) : seul le proprietaire peut supprimer son fichier dans un repertoire partage

    chmod +t /tmp

## ACL (Access Control Lists)

Pour des permissions plus fines que le modele POSIX :

    getfacl fichier.txt
    setfacl -m u:alice:rwx fichier.txt
    setfacl -x u:alice fichier.txt

## Problemes courants

Permission denied : verifier `ls -l`, verifier l'utilisateur courant avec `whoami`, verifier les groupes avec `groups`.

Execution refusee : verifier que le bit x est present avec `chmod +x`.

Ecrire impossible : verifier le proprietaire et les permissions d'ecriture.

## Actions correctives

1. Identifier le proprietaire avec `ls -l`
2. Verifier l'utilisateur et les groupes de l'appelant
3. Ajuster les permissions avec `chmod` de maniere minimale (principe du moindre privilege)
4. Utiliser `sudo` temporairement si necessaire
5. Pour les cas complexes : utiliser les ACL avec `setfacl`
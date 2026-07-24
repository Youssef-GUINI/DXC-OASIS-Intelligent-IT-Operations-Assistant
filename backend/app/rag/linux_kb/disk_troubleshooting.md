# Diagnostic Disque sur Linux

## Verification de l'espace disque

La commande `df -h` affiche l'espace utilise et disponible pour chaque partition montee. Surveillez particulierement les partitions a plus de 80% d'usage.

La commande `du -sh /var/log/*` permet d'identifier rapidement quels reperoires consomment le plus d'espace.

## Disque plein : causes frequentes

Les logs qui tournent en boucle ou qui ne sont pas rottes peuvent remplir une partition. Verifiez `/var/log/` et la configuration de `logrotate`.

Les fichiers temporaires non nettoyes dans `/tmp` ou `/var/tmp` peuvent aussi saturer l'espace.

Un core dump oublié dans le repertoire de l'application peut occuper plusieurs gigaoctets.

## Recherche de gros fichiers

Pour trouver les 20 plus gros fichiers sur le systeme :

    find / -type f -size +100M -exec ls -lh {} \; 2&gt;/dev/null | head -n 20

Pour analyser l'espace par repertoire :

    ncdu /

## IO Wait eleve

Un `iowait` eleve dans `top` ou `iostat` indique que le CPU attend le disque. Cela peut signaler un disque dur defectueux, un RAID en rebuild ou une charge IO excessive.

    iostat -x 1 5

Surveillez la colonne `%util` : si elle approche 100%, le disque est surcharge.

## SMART et sante du disque

Verifiez l'etat SMART du disque :

    smartctl -a /dev/sda

Recherchez les attributs `Reallocated_Sector_Ct`, `Current_Pending_Sector` et `Offline_Uncorrectable`. Des valeurs non nules indiquent une degradation physique.

## Actions correctives

1. Nettoyer les logs anciens avec `journalctl --vacuum-time=7d`
2. Vider le cache des paquets : `apt-get clean` ou `yum clean all`
3. Supprimer les fichiers temporaires non utilises
4. Si le disque est plein legitimement : etendre le volume ou ajouter un disque
5. Si SMART indique une defaillance : planifier le remplacement du disque
# Diagnostic Memoire sur Linux

## Verification de l'usage memoire

La commande `free -h` affiche un resume lisible de l'usage memoire totale, utilisee, libre et en cache. La colonne `available` est la plus importante car elle inclut la memoire liberable depuis les caches.

La commande `vmstat 1 5` affiche des statistiques systeme toutes les secondes pendant 5 iterations. Les colonnes `si` (swap in) et `so` (swap out) indiquent si le systeme swappe.

## Detection d'une fuite memoire

Une fuite memoire se manifeste par une augmentation continue de l'usage RAM sans liberation, jusqu'a saturation. Utilisez :

    ps aux --sort=-%mem | head -n 10

Pour surveiller un processus specifique dans le temps :

    watch -n 1 'ps -p &lt;PID&gt; -o pid,rss,vsz,cmd'

Si la valeur RSS (Resident Set Size) augmente indefiniment, il y a probablement une fuite memoire.

## OOM Killer

Lorsque la memoire est saturee, le OOM Killer (Out Of Memory) tue automatiquement le processus le plus gourmand pour liberer de la RAM. Consultez les logs OOM avec :

    dmesg | grep -i "out of memory"
    journalctl -k | grep -i "killed process"

## Gestion du Swap

Verifiez l'usage du swap avec `swapon -s` ou `cat /proc/swaps`. Un usage eleve de swap degrade fortement les performances.

Pour vider le swap (si la RAM est disponible) :

    sudo swapoff -a && sudo swapon -a

## Actions correctives

1. Identifier le processus gourmand avec `ps aux --sort=-%mem`
2. Redemarrer le service fautif si c'est un service connu
3. Augmenter la RAM physique si le besoin est legitime
4. Ajouter ou augmenter le swap si la RAM est insuffisante
5. Configurer `vm.swappiness` dans `/etc/sysctl.conf` pour ajuster la tendance au swap (valeur par defaut 60, baisser a 10 pour les serveurs)
# Diagnostic CPU sur Linux

## Vérification rapide de l'usage CPU

Pour verifier l'usage CPU en temps reel, utilisez la commande `top`. Elle affiche les processus consommant le plus de ressources, triee par pourcentage CPU.

La commande `htop` offre une interface plus lisible avec des couleurs, un tri interactif et une navigation au clavier. Elle necessite souvent une installation via le gestionnaire de paquets.

## CPU bloque a 100% : procedure de diagnostic

Si le CPU est bloque a 100% de maniere persistante, verifiez d'abord s'il s'agit d'un seul processus avec :

    ps aux --sort=-%cpu | head -n 10

Cette commande liste les 10 processus les plus gourmands en CPU. Notez le PID et le nom du processus en tete de liste.

## Causes frequentes d'un CPU a 100%

Un processus zombie ou une boucle infinie dans un script sont des causes frequentes. Un processus zombie a un etat Z dans la colonne STAT de `ps aux`.

Une boucle infinie dans un script shell ou Python consomme un coeur complet. Identifiez le script avec `ps aux` puis consultez son contenu ou ses logs.

## Analyse par coeur

La commande `mpstat -P ALL 1` permet de voir l'usage par coeur individuellement, utile pour detecter un desequilibre de charge sur un systeme multi-coeurs. Elle fait partie du paquet `sysstat`.

Si un seul coeur est surcharge, cela peut indiquer un processus mono-thread mal optimise ou une interruption materielle mal repartie.

## Taches planifiees suspectes

En cas de charge elevee inexpliquee, verifiez les taches planifiees :

    crontab -l
    sudo cat /etc/crontab
    ls /etc/cron.d/

Une tache mal configuree qui se declenche en boucle ou trop frequemment peut saturer le CPU.

## Actions correctives

1. Identifier le processus fautif avec `top` ou `ps`
2. Verifier si le processus est legitime (service attendu ou processus inconnu)
3. Pour un processus inconnu : inspecter son chemin avec `ls -l /proc/&lt;PID&gt;/exe`
4. Si necessaire : tuer le processus avec `kill -15 &lt;PID&gt;` (SIGTERM) puis `kill -9 &lt;PID&gt;` (SIGKILL) si persistant
5. Pour un service legitime en surconsommation : consulter ses logs et redemarrer le service
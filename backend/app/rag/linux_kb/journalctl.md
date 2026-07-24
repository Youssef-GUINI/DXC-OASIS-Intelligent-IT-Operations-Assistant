# Utilisation de journalctl

## Principe

journalctl est l'outil de consultation des logs de systemd. Les logs sont stockes dans un format binaire dans `/var/log/journal/`.

## Commandes de base

Afficher tous les logs :

    journalctl

Afficher les logs depuis le dernier boot :

    journalctl -b

Afficher les logs en temps reel :

    journalctl -f

## Filtrage par service

Logs d'un service specifique :

    journalctl -u nginx

Logs d'un service depuis le dernier boot :

    journalctl -u nginx -b

## Filtrage par priorite

Niveaux de priorite : emerg, alert, crit, err, warning, notice, info, debug.

Afficher uniquement les erreurs :

    journalctl -p err

Afficher les erreurs et alertes :

    journalctl -p err..alert

## Filtrage temporel

Depuis une date :

    journalctl --since "2026-07-20 10:00:00"

Depuis hier :

    journalctl --since yesterday

Plage horaire :

    journalctl --since "2026-07-20 09:00" --until "2026-07-20 12:00"

## Nettoyage des logs

La journalisation peut consommer beaucoup d'espace disque.

Conserver uniquement les 7 derniers jours :

    sudo journalctl --vacuum-time=7d

Limiter a une taille maximale :

    sudo journalctl --vacuum-size=500M

## Actions correctives

1. Utiliser `-f` pour le debug en temps reel
2. Utiliser `-u` pour isoler les logs d'un service
3. Utiliser `--since` pour investiguer un incident a une heure precise
4. Nettoyer regulierement les anciens logs pour economiser l'espace disque
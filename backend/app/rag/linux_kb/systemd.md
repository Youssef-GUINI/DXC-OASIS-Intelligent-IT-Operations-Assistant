# Gestion des Services avec systemd

## Commandes de base

Lister tous les services :

    systemctl list-units --type=service --state=running

Lister les services actifs :

    systemctl --type=service --state=active

Afficher l'etat d'un service :

    systemctl status nginx

## Demarrer, arreter, redemarrer

    sudo systemctl start nginx
    sudo systemctl stop nginx
    sudo systemctl restart nginx

Recharger la configuration sans coupure :

    sudo systemctl reload nginx

Activer au demarrage :

    sudo systemctl enable nginx

Desactiver au demarrage :

    sudo systemctl disable nginx

## Logs d'un service

Afficher les logs d'un service :

    sudo journalctl -u nginx

Suivre les logs en temps reel :

    sudo journalctl -u nginx -f

Logs depuis le dernier demarrage :

    sudo journalctl -u nginx --since today

## Analyse du boot

Analyser le temps de demarrage :

    systemd-analyze

Identifier les services les plus lents au boot :

    systemd-analyze blame

## Unite en etat failed

Si un service est en failed :

    systemctl list-units --failed
    systemctl status &lt;service&gt;
    sudo journalctl -u &lt;service&gt; --no-pager

## Actions correctives

1. Verifier le statut avec `systemctl status`
2. Consulter les logs avec `journalctl -u`
3. Tester la configuration avant reload : `nginx -t`
4. Redemarrer le service apres correction
5. Si le service echoue au boot : verifier les dependances avec `systemctl list-dependencies`
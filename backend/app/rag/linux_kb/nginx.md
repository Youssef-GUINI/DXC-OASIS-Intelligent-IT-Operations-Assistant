# Administration Nginx

## Verification de l'etat

Verifier que Nginx est actif :

    sudo systemctl status nginx

Verifier les processus :

    ps aux | grep nginx

## Test de la configuration

Avant tout reload ou restart, tester la syntaxe :

    sudo nginx -t

Cette commande detecte les erreurs de syntaxe sans interrompre le service.

## Configuration des sites

Les fichiers de configuration des sites virtuels sont dans :

    /etc/nginx/sites-available/    (Debian/Ubuntu)
    /etc/nginx/conf.d/             (RHEL/CentOS)

Les sites actifs sont lies symboliquement depuis `sites-enabled`.

Activer un site :

    sudo ln -s /etc/nginx/sites-available/mon-site /etc/nginx/sites-enabled/
    sudo nginx -t
    sudo systemctl reload nginx

## Logs Nginx

Logs d'acces :

    /var/log/nginx/access.log

Logs d'erreur :

    /var/log/nginx/error.log

Suivre les erreurs en temps reel :

    sudo tail -f /var/log/nginx/error.log

## Erreurs courantes

502 Bad Gateway : Nginx ne peut pas joindre le backend (PHP-FPM, uWSGI, etc.). Verifiez que le service backend est actif.

403 Forbidden : probleme de permissions sur les fichiers statiques. Verifiez `user` dans nginx.conf et les permissions du repertoire.

404 Not Found : le fichier ou la location n'existe pas. Verifiez la directive `root` et `location`.

## Actions correctives

1. Toujours tester avec `nginx -t` avant reload
2. Verifier les permissions des repertoires web
3. Consulter `/var/log/nginx/error.log` en cas d'erreur
4. Verifier que le port 80/443 n'est pas occupe : `ss -tlnp`
5. Redemarrer avec `systemctl restart nginx` si necessaire
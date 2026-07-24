# Administration Apache HTTP Server

## Verification de l'etat

Verifier que Apache est actif :

    sudo systemctl status apache2        (Debian/Ubuntu)
    sudo systemctl status httpd          (RHEL/CentOS)

## Test de la configuration

Tester la syntaxe sans redemarrer :

    sudo apachectl configtest

Ou :

    sudo httpd -t

## Structure des fichiers de configuration

Debian/Ubuntu :
- `/etc/apache2/apache2.conf` : configuration principale
- `/etc/apache2/sites-available/` : sites virtuels disponibles
- `/etc/apache2/sites-enabled/` : sites actifs (liens symboliques)
- `/etc/apache2/mods-available/` : modules disponibles
- `/etc/apache2/mods-enabled/` : modules actifs

RHEL/CentOS :
- `/etc/httpd/conf/httpd.conf` : configuration principale
- `/etc/httpd/conf.d/` : sites virtuels et modules

## Activer un site ou un module

    sudo a2ensite mon-site
    sudo a2enmod rewrite
    sudo systemctl reload apache2

## Logs Apache

Logs d'erreur :

    /var/log/apache2/error.log    (Debian)
    /var/log/httpd/error_log      (RHEL)

Logs d'acces :

    /var/log/apache2/access.log   (Debian)
    /var/log/httpd/access_log     (RHEL)

## Erreurs courantes

AH00558 : Apache ne peut pas determiner le nom de domaine. Ajoutez `ServerName localhost` dans la config.

Permission denied : verifier les permissions du repertoire `DocumentRoot` et l'utilisateur sous lequel Apache tourne (`www-data` ou `apache`).

Module manquant : verifier avec `apachectl -M` que le module necessaire est charge.

## Actions correctives

1. Tester la config avec `apachectl configtest`
2. Consulter les logs d'erreur
3. Verifier les permissions du DocumentRoot
4. Activer les modules necessaires avec `a2enmod`
5. Redemarrer avec `systemctl restart apache2`
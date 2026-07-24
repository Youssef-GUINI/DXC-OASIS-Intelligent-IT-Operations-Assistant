# Diagnostic DNS sur Linux

## Fichiers de configuration

Le fichier `/etc/resolv.conf` contient les serveurs DNS utilises par le systeme. Sur les systemes modernes avec systemd-resolved, c'est souvent un lien symbolique.

Le fichier `/etc/hosts` permet de surcharger les DNS localement. Verifiez qu'il ne contient pas d'entrees obsoletes ou incorrectes.

## Test de resolution

Resoudre un nom de domaine avec dig :

    dig google.com

Resoudre avec un serveur DNS specifique :

    dig @8.8.8.8 google.com

La section `ANSWER SECTION` doit contenir les enregistrements A.

Tester la resolution inverse :

    dig -x 8.8.8.8

## Cache DNS

Vider le cache DNS si systemd-resolved est actif :

    sudo systemd-resolve --flush-caches

Ou :

    sudo resolvectl flush-caches

## Problemes courants

Resolution lente : verifier la latence vers les serveurs DNS dans `/etc/resolv.conf`. Un serveur DNS inaccessible ralentit toutes les requetes.

NXDOMAIN : le domaine n'existe pas ou le DNS ne le connait pas. Verifiez l'orthographe.

SERVFAIL : le serveur DNS a rencontre une erreur. Essayez un autre serveur DNS.

## Actions correctives

1. Verifier `/etc/resolv.conf` et ajouter des serveurs DNS fiables (8.8.8.8, 1.1.1.1)
2. Vider le cache DNS
3. Verifier que le service systemd-resolved fonctionne : `systemctl status systemd-resolved`
4. Tester avec `dig` et `nslookup` pour isoler le probleme
5. Verifier les regles firewall sortantes sur le port 53 UDP/TCP
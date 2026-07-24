# Diagnostic Reseau sur Linux

## Verification des interfaces

Afficher les interfaces reseau et leurs adresses IP :

    ip addr show

Ou la version legacy :

    ifconfig -a

Verifier l'etat des interfaces (UP/DOWN) :

    ip link show

## Connectivite de base

Tester la connectivite vers une IP :

    ping -c 4 8.8.8.8

Tester la resolution DNS :

    ping -c 4 google.com

Si la ping IP fonctionne mais pas le nom de domaine, le probleme est DNS.

## Table de routage

Afficher la table de routage :

    ip route show

Ou :

    route -n

Verifier la passerelle par defaut :

    ip route | grep default

## Ports ouverts et connexions

Lister les ports en ecoute :

    ss -tlnp

Ou :

    netstat -tlnp

Verifier les connexions etablies :

    ss -tan

## Firewall

Verifier les regles iptables :

    sudo iptables -L -v -n

Verifier firewalld (RHEL/CentOS) :

    sudo firewall-cmd --list-all

Verifier UFW (Ubuntu/Debian) :

    sudo ufw status verbose

## Capture de paquets

Capturer le trafic sur une interface :

    sudo tcpdump -i eth0 -w capture.pcap

Analyser avec Wireshark ou tshark.

## Actions correctives

1. Verifier que l'interface est UP avec `ip link set eth0 up`
2. Verifier la configuration IP (statique ou DHCP)
3. Tester la passerelle par defaut avec `traceroute`
4. Verifier que le port n'est pas bloque par le firewall
5. Redemarrer le service reseau si necessaire : `systemctl restart NetworkManager`
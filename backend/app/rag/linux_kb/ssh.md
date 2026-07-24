# Diagnostic SSH sur Linux

## Verification du service

Verifier que le service SSH est actif :

    sudo systemctl status sshd

Ou sur Debian/Ubuntu :

    sudo systemctl status ssh

Redemarrer le service :

    sudo systemctl restart sshd

## Connexion refusee

Si la connexion est refusee :

1. Verifier que le service ecoute sur le bon port : `ss -tlnp | grep ssh`
2. Verifier le port dans `/etc/ssh/sshd_config` (par defaut 22)
3. Verifier que le firewall autorise le port SSH

## Authentification par cle

Generer une paire de cles :

    ssh-keygen -t ed25519 -C "commentaire"

Copier la cle publique sur le serveur distant :

    ssh-copy-id user@server

Les cles autorisees sont stockees dans `~/.ssh/authorized_keys` sur le serveur.

## Permissions des fichiers SSH

Les permissions doivent etre strictes :

    chmod 700 ~/.ssh
    chmod 600 ~/.ssh/id_ed25519
    chmod 644 ~/.ssh/id_ed25519.pub
    chmod 600 ~/.ssh/authorized_keys

Des permissions trop ouvertes peuvent empecher l'authentification par cle.

## Logs SSH

Les logs de connexion sont dans :

    /var/log/auth.log        (Debian/Ubuntu)
    /var/log/secure          (RHEL/CentOS)

Ou via journalctl :

    sudo journalctl -u sshd -f

## Actions correctives

1. Verifier que le service est actif et ecoute
2. Verifier les permissions des fichiers ~/.ssh
3. Consulter les logs pour identifier l'erreur exacte
4. Tester avec verbose : `ssh -vvv user@server`
5. Si le root est bloque : verifier `PermitRootLogin` dans sshd_config
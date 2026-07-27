# Runbook Storage - Echec d'une sauvegarde nocturne

## Objectif

Cette procedure sert a diagnostiquer un job de sauvegarde nocturne en echec
avant toute relance manuelle. Elle s'applique aux jobs planifies du workspace
Storage & Backup.

## Informations a collecter

Avant toute action, relever dans la console de sauvegarde :

1. le nom du job et son identifiant ;
2. l'heure de debut, l'heure d'echec et le code d'erreur ;
3. le serveur ou la ressource source concernee ;
4. le repository de sauvegarde cible ;
5. le dernier point de restauration valide.

Ne relancez pas le job tant que le code d'erreur et le repository cible n'ont
pas ete verifies.

## Controle prioritaire : capacite du repository

Un repository dont l'espace libre est inferieur a 15 pour cent doit etre traite
comme un incident de capacite. Verifier la capacite disponible et la croissance
recente des sauvegardes avant de relancer le job.

Si le seuil de 15 pour cent est atteint :

1. ne supprimez aucune sauvegarde sans validation ;
2. verifiez la politique de retention applicable ;
3. identifiez les sauvegardes expirees candidates a une suppression approuvee ;
4. escaladez vers le responsable Storage si aucune capacite ne peut etre liberee
   sans risque.

## Codes d'erreur frequents

### E-BKP-042 - Repository plein ou quota depasse

Verifier l'espace libre, le quota associe au job et les erreurs d'ecriture du
repository. Ne relancez le job qu'apres retour a une capacite libre superieure
a 15 pour cent.

### E-BKP-101 - Authentification de la ressource source echouee

Verifier que le compte de service est actif, que son mot de passe n'a pas expire
et que les droits de lecture de la ressource source sont toujours presents.

### E-BKP-207 - Delai d'attente ou indisponibilite reseau

Verifier la connectivite entre le serveur de sauvegarde, la ressource source et
le repository. Consulter les erreurs reseau a l'heure exacte de l'echec.

## Verification d'integrite

Avant une relance, confirmer que le dernier point de restauration valide est
lisible. Si le dernier point est douteux, ouvrir un incident prioritaire et ne
pas lancer de restauration sans confirmation explicite.

## Relance controlee

La relance d'un job est une action operationnelle. Elle doit etre faite apres
correction de la cause, avec une surveillance du journal du job jusqu'a sa
fin. Documenter le code d'erreur, la cause retenue et le resultat de la relance
dans le ticket d'incident.

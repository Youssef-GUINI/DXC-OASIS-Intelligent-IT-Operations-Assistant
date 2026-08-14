---
id: rb-veeam_entire_vm_restore
title: Restauration complète d'une machine virtuelle avec Veeam
keywords:
  - Veeam
  - Restauration
  - Machine virtuelle
mcp_read_tools:
  - get_backup_files
  - list_vm_disks
mcp_action_tools:
  - restore_entire_vm
  - resize_vm_disk
risk_level: "HIGH"
---

# Restauration complète d'une machine virtuelle avec Veeam

## 1. Symptômes & Déclencheurs Storage
La restauration complète d'une machine virtuelle est nécessaire lorsque la machine virtuelle d'origine est défaillante ou lorsqu'il est nécessaire de restaurer une machine virtuelle à un état antérieur.

## 2. Procédure de Diagnostic (Inquiry)
Avant de procéder à la restauration, il est nécessaire de vérifier les éléments suivants :
* La machine virtuelle est-elle défaillante ou est-elle nécessaire de la restaurer à un état antérieur ?
* Les fichiers de sauvegarde sont-ils disponibles et valides ?
* Les disques de la machine virtuelle sont-ils configurés correctement ?

## 3. Arbre de Décision & Actions de Remédiation
### Étape 1 : Sélectionner le mode de transport
* Si le proxy de sauvegarde est connecté directement au tissu SAN ou a accès aux datastores NFS, utiliser le mode de transport Direct storage access.
* Si le proxy de sauvegarde est virtualisé et résidé sur l'hôte ESXi à restaurer, utiliser le mode de transport Virtual appliance.
* Sinon, utiliser le mode de transport Network.

### Étape 2 : Restaurer la machine virtuelle
* Utiliser l'outil `restore_entire_vm` pour restaurer la machine virtuelle à partir du fichier de sauvegarde.
* Configurer les paramètres de la machine virtuelle tels que le nom, l'hôte, le datastore, le format de disque et les propriétés réseau.

### Étape 3 : Vérifier la restauration
* Vérifier que la machine virtuelle est restaurée correctement et qu'elle est en cours d'exécution.
* Vérifier que les disques de la machine virtuelle sont restaurés correctement et qu'ils sont accessibles.
---
id: rb-truenas_pool_management
title: Gestion des Pools TrueNAS
keywords:
  - TrueNAS
  - Pools
  - Storage
mcp_read_tools:
  - get_pool_status
  - list_vdevs
mcp_action_tools:
  - create_pool
  - delete_pool
  - expand_pool
  - upgrade_pool
  - replace_disk
risk_level: "HIGH"

# Gestion des Pools TrueNAS

## 1. Symptômes & Déclencheurs Storage
Les symptômes et déclencheurs pour la gestion des pools TrueNAS incluent :
* La nécessité d'augmenter la capacité de stockage
* La nécessité de remplacer des disques défectueux
* La nécessité de mettre à niveau la version de TrueNAS
* La nécessité de configurer les paramètres de pool

## 2. Procédure de Diagnostic (Inquiry)
La procédure de diagnostic pour la gestion des pools TrueNAS inclut :
* Vérifier l'état du pool et des disques
* Vérifier les paramètres de pool et de VDEV
* Vérifier les journaux de système pour les erreurs ou les avertissements

## 3. Arbre de Décision & Actions de Remédiation
L'arbre de décision pour la gestion des pools TrueNAS inclut :
* Si le pool est sain, mais la capacité est insuffisante :
 + Ajouter des disques au pool
 + Mettre à niveau la version de TrueNAS pour utiliser de nouvelles fonctionnalités
* Si le pool est endommagé ou si des disques sont défectueux :
 + Remplacer les disques défectueux
 + Réparer le pool si possible
* Si la version de TrueNAS est obsolète :
 + Mettre à niveau la version de TrueNAS
 + Vérifier les paramètres de pool et de VDEV après la mise à niveau
* Si les paramètres de pool ou de VDEV sont incorrects :
 + Configurer les paramètres de pool et de VDEV correctement
 + Vérifier l'état du pool et des disques après la configuration
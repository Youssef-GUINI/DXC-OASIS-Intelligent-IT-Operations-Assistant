# OASIS AI Copilot — Rapport d'avancement (Suivi des incidents) + État global

## Objectif de ce document

Ce rapport fait suite aux rapports précédents (étapes 1-2, 3-4, étape 5 +
guide Storage). Il détaille l'ajout du système de suivi de statut des
incidents (ouvert/résolu, automatique et manuel) côté Linux, et fait le point
complet sur l'état du projet pour faciliter la coordination avec le binôme.

---

## Contexte : pourquoi cet ajout

La détection automatique d'incidents (ajoutée précédemment, voir rapport
étape 5) créait des entrées en base à chaque anomalie détectée, mais rien ne
permettait de savoir si un problème signalé était toujours d'actualité ou
déjà réglé. Un incident restait figé pour toujours, sans distinction entre
"encore actif" et "résolu". Ce système comble ce manque.

---

## Ce qui a été ajouté au modèle `Incident`

Trois nouvelles colonnes sur la table `incidents` :

| Colonne | Type | Rôle |
|---|---|---|
| `category` | texte, optionnel | Type de problème détecté automatiquement : `"cpu"`, `"ram"`, `"disk"`, `"services"`, `"network"`. Vide pour les incidents créés via le chat. |
| `status` | texte, obligatoire | `"open"` (actif) ou `"resolved"` (réglé). `"open"` par défaut à la création. |
| `resolved_at` | date/heure, optionnel | Horodatage exact du passage à `"resolved"`. Utile pour un futur calcul de "temps moyen de résolution" (KPI prévu section 12 de l'architecture officielle). |

## Les deux mécanismes de résolution

### 1. Résolution automatique

Le scheduler de détection (qui tourne toutes les 5 minutes) vérifie CPU, RAM,
disque, services, réseau. Pour chaque catégorie, la logique est désormais
symétrique :

```
Seuil depasse       -> cree un nouvel incident "open" pour cette categorie
Seuil pas depasse    -> resout automatiquement tous les incidents "open"
                        deja existants pour cette categorie
```

Implémenté dans `app/services/incident_service.py`, fonction
`auto_resolve_by_category(db, persona, category)` : cherche tous les
incidents `open` d'une persona/catégorie donnée, les bascule à `resolved`
avec l'heure actuelle.

Appelée depuis `app/monitoring/incident_detector.py`, une fois par catégorie
à chaque cycle du scheduler (branche `else` de chaque vérification de seuil).

**Exemple concret observé pendant les tests** : le scheduler a détecté
`sshd` en échec (`category="services"`, `status="open"`). À un cycle
suivant, si `sshd` repasse à l'état actif, le système résout automatiquement
cet incident sans intervention humaine.

### 2. Résolution manuelle

Un ingénieur peut aussi marquer explicitement un incident comme réglé, via
une nouvelle route API :

```
PATCH /api/v1/linux/incidents/{incident_id}/resolve
```

Le verbe `PATCH` est utilisé car on modifie partiellement une ressource
existante (juste le statut), pas la totalité de l'incident. Implémenté via
`resolve_incident(db, incident_id)` dans `incident_service.py` — recherche
l'incident par id, bascule `status` à `resolved`, remplit `resolved_at`.

## Consultation des incidents

Nouvelle route de lecture :

```
GET /api/v1/linux/incidents
GET /api/v1/linux/incidents?status_filter=open
GET /api/v1/linux/incidents?status_filter=resolved
```

Implémentée via `list_incidents(db, status, persona)` — construit
dynamiquement le filtre SQL selon les paramètres fournis, trie du plus
récent au plus ancien.

## Fichiers modifiés ou créés

```
backend/app/
├── models/incident.py              (colonnes category, status, resolved_at ajoutées)
├── schemas/incident.py             (nouveau — IncidentResponse pour l'API)
├── services/incident_service.py    (list_incidents, resolve_incident,
│                                     auto_resolve_by_category ajoutes)
├── monitoring/incident_detector.py (logique auto-resolution ajoutee par categorie)
└── api/v1/linux.py                 (routes GET /incidents et
                                      PATCH /incidents/{id}/resolve ajoutees)
```

## Résultat vérifié

| Test | Résultat |
|---|---|
| `GET /linux/incidents` (sans filtre) | `200 OK`, liste complète triée par date |
| `GET /linux/incidents?status_filter=open` | `200 OK`, uniquement les incidents actifs |
| `GET /linux/incidents?status_filter=resolved` | `200 OK`, uniquement les incidents réglés |
| `PATCH /linux/incidents/24/resolve` | `200 OK`, `status` passé à `resolved`, `resolved_at` rempli — confirmé aussi directement en base PostgreSQL |

## Problème rencontré et corrigé (à connaître pour éviter de le reproduire)

Lors de l'écriture de la migration Alembic ajoutant les 3 colonnes, un
copier-coller dans l'éditeur a fait qu'une ligne de code
(`op.add_column(...)` pour `status`) s'est retrouvée collée **à l'intérieur
du docstring** en haut du fichier de migration (le texte entre `"""..."""`),
au lieu d'être une instruction exécutable. Comme un docstring accepte
n'importe quel texte, Python n'a signalé aucune erreur de syntaxe — mais
cette ligne ne s'est jamais exécutée. Résultat : la migration s'est
"appliquée avec succès" en ajoutant seulement 2 colonnes sur 3
(`category`, `resolved_at`), la base réelle divergeant silencieusement du
modèle Python qui, lui, connaissait bien `status`.

**Symptôme** : erreur `column incidents.status does not exist` dès qu'une
route touchant aux incidents était appelée, alors que la migration semblait
être passée sans erreur.

**Correction retenue** : plutôt que de rouvrir une migration déjà marquée
comme appliquée (source de confusion sur l'état réel), création d'une
**nouvelle migration séparée**, écrite à la main (pas générée par
`--autogenerate`), qui ajoute uniquement la colonne manquante.

**Règle à suivre systématiquement après une migration** (ajoutée à la liste
de vigilance des rapports précédents) :
1. Modifier le modèle Python
2. Générer : `alembic revision --autogenerate -m "description"`
3. **Toujours afficher le contenu du fichier généré avant de l'appliquer**
   (`Get-Content chemin\vers\le\fichier.py`) — vérifier que chaque
   `op.add_column(...)` attendu est bien une ligne de code à l'intérieur de
   `upgrade()`, pas du texte dans le docstring
4. Appliquer : `alembic upgrade head`
5. Vérifier en base que les colonnes existent réellement
   (`\d nom_table`, ou requête sur `information_schema.columns`)

---

## État global du projet — vue d'ensemble pour le binôme

```
✅ Étape 1 — Fondations (Docker, PostgreSQL, modèles, migrations, seed)
✅ Étape 2 — Authentification (JWT, hashing bcrypt, route protégée, RBAC prêt)
✅ Étape 3 — Persona Linux minimal (LLM Router, Groq, premier chat)
✅ Étape 4 — RAG (Knowledge CMS, ChromaDB, recherche sémantique)
✅ Étape 5 — MCP (Linux Server/Client, tool-calling fonctionnel)
✅ Extension — Détection automatique d'incidents (scheduler + seuils)
✅ Extension — Suivi de statut des incidents (open/resolved, auto + manuel)
⬜ Étape 6 — Storage (en cours côté binôme — voir guide dédié fourni précédemment)
⬜ Reports — génération de rapport à partir d'un/plusieurs incidents
⬜ Dashboard/KPIs Linux
⬜ Frontend Linux Workspace
⬜ Étape 7 — Orchestrateur central + Cross-Domain (à faire ensemble, une fois
             Linux ET Storage complets)
⬜ Étape 8 (restant) — Admin Workspace, Frontend Storage Workspace
```

### Ce qui reste à faire côté Linux (cette session)

1. **Reports** : génération d'un document technique (probablement PDF, via
   ReportLab comme prévu section 11 de l'architecture) à partir d'un ou
   plusieurs incidents — résumé, root cause analysis, outils MCP utilisés,
   recommandations
2. **Dashboard/KPIs Linux** : agrégation de métriques déjà présentes en base
   (nombre d'incidents résolus, temps moyen de résolution grâce à
   `resolved_at`, usage des LLM, appels MCP) pour affichage
3. **Frontend Linux Workspace** : les 5 écrans prévus (Dashboard, Chat,
   Incident History, Reports, KPIs) consommant les routes déjà construites

### Ce qui reste côté Storage (binôme)

Suivre le guide détaillé fourni dans le rapport précédent (Étape 5 + Guide
Storage) : reproduire à l'identique le pattern Linux (outils MCP, RAG,
Persona, route API), avec les pièges déjà rencontrés listés pour les éviter
d'emblée.

**Note pour le binôme** : le système de suivi de statut des incidents
(`status`, `category`, `resolved_at`) documenté ici s'applique au modèle
`Incident` **partagé** entre les deux Personas (le champ `persona` distingue
déjà `"linux_persona"` de `"storage_persona"` dans la même table) — donc
côté Storage, il n'y a **rien à recréer** pour cette partie : `save_incident`,
`list_incidents`, `resolve_incident` sont directement réutilisables en
passant `persona="storage_persona"`. Seule la détection automatique
(`incident_detector.py` et ses seuils) est spécifique à Linux pour l'instant
— un équivalent `detect_storage_incidents()` serait à écrire côté Storage
sur le même modèle si cette fonctionnalité doit aussi s'appliquer là-bas.

### Une fois Linux ET Storage terminés

Session commune pour l'Étape 7 (Orchestrateur central + Cross-Domain) — elle
touche aux deux composants et a plus de sens à construire ensemble.

---

## Identifiants de test (rappel)

| Email | Mot de passe | Rôle |
|---|---|---|
| `linux@oasis.com` | `linux123` | linux_engineer |
| `storage@oasis.com` | `storage123` | storage_engineer |
| `admin@oasis.com` | `admin123` | administrator |

## Comment relancer le projet

```powershell
docker compose up -d
cd backend
uvicorn app.main:app --reload
# Puis http://127.0.0.1:8000/docs
```

## Nouvelles routes disponibles (à tester)

```
GET   /api/v1/linux/incidents                          -> tous les incidents
GET   /api/v1/linux/incidents?status_filter=open        -> incidents actifs
GET   /api/v1/linux/incidents?status_filter=resolved    -> incidents résolus
PATCH /api/v1/linux/incidents/{incident_id}/resolve     -> résoudre manuellement
```

# OASIS AI Copilot — Rapport d'avancement (Étapes 1 & 2)

## Objectif de ce document

Ce rapport résume le travail réalisé sur le backend, pour que le binôme du projet
comprenne ce qui a été fait, pourquoi, et puisse reprendre le développement en
connaissance de cause. Il couvre les deux premières étapes du plan de
développement défini pour le sprint (sur les 8 étapes prévues au total).

---

## Étape 1 — Fondations (Docker + Base de données)

### Objectif
Mettre en place l'infrastructure minimale sans laquelle rien ne peut fonctionner :
la base de données PostgreSQL, la base vectorielle ChromaDB (pour le RAG,
utilisée plus tard), et les deux premières tables (`users`, `roles`).

### Ce qui a été fait

**1. Environnement Docker**
- `docker-compose.yml` à la racine du projet définit deux services :
  - `db` (PostgreSQL 16) — la base de données principale
  - `chromadb` (ChromaDB) — la base vectorielle pour le RAG (Knowledge CMS)
- Les deux tournent dans des conteneurs isolés, démarrés en une seule commande
  (`docker compose up -d`), avec des volumes Docker pour persister les données
  entre les redémarrages.
- Les ports sont exposés vers la machine locale : `5432` pour Postgres, `8001`
  pour ChromaDB (mappé sur le port interne `8000` pour éviter tout conflit avec
  un futur serveur FastAPI local sur le port 8000).

**2. Configuration via `.env`**
- Toutes les valeurs sensibles (identifiants Postgres, clé secrète JWT, futures
  clés API LLM) sont externalisées dans des fichiers `.env`, jamais codées en
  dur dans le code.
- Deux fichiers `.env` distincts existent :
  - `.env` à la racine → utilisé par `docker-compose.yml`
  - `backend/.env` → utilisé par le backend FastAPI, qui tourne pour l'instant
    **en local** (hors Docker), donc pointe vers `localhost:5432` et non `db`
    (le nom `db` n'est résolvable que depuis l'intérieur du réseau Docker).
- `.gitignore` a été configuré pour exclure `.env`, `.venv/`, `node_modules/`
  et autres artefacts, afin de ne jamais committer de secrets ni de
  dépendances volumineuses.

**3. Connexion à la base de données (SQLAlchemy)**
- `backend/app/core/config.py` centralise la lecture des variables
  d'environnement via Pydantic Settings — un seul point d'entrée pour la config,
  plutôt que des appels dispersés à `os.getenv()`.
- `backend/app/database/base.py` déclare la classe de base SQLAlchemy
  (`Base`) dont hériteront tous les modèles.
- `backend/app/database/session.py` gère la connexion réelle (`engine`) et
  fournit `get_db()`, une dependency FastAPI qui ouvre une session par requête
  et la ferme proprement, même en cas d'erreur.

**4. Modèles de données (SQLAlchemy)**
- `backend/app/models/role.py` — table `roles` (id, name)
- `backend/app/models/user.py` — table `users` (id, email, hashed_password,
  full_name, is_active, created_at, role_id → clé étrangère vers `roles`)
- `backend/app/models/__init__.py` centralise l'import de tous les modèles —
  nécessaire pour que SQLAlchemy puisse résoudre les relations entre classes
  (ex: `User.role`) au démarrage de l'application.

**5. Migrations (Alembic)**
- Alembic génère et applique les changements de structure de la base de
  données à partir des modèles Python, avec un historique versionné (comme
  Git, mais pour le schéma SQL).
- `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`
  configurés pour se connecter à la bonne base et détecter tous les modèles.
- Première migration générée et appliquée : création des tables `users` et
  `roles`, avec la contrainte unique sur `email`, la contrainte de clé
  étrangère `role_id → roles.id`, et les index appropriés.

**6. Données de test (seed)**
- `backend/app/database/seed.py` — script idempotent (rejouable sans
  dupliquer les données) qui crée :
  - Les 3 rôles définis dans l'architecture officielle : `linux_engineer`,
    `storage_engineer`, `administrator`
  - 3 utilisateurs de test, un par rôle, avec mot de passe hashé en bcrypt

### Identifiants de test disponibles

| Email | Mot de passe | Rôle |
|---|---|---|
| `linux@oasis.com` | `linux123` | linux_engineer |
| `storage@oasis.com` | `storage123` | storage_engineer |
| `admin@oasis.com` | `admin123` | administrator |

### Résultat vérifié
- `docker compose ps` → `oasis_postgres` (healthy), `oasis_chromadb` (running)
- `\dt` dans Postgres → tables `roles`, `users`, `alembic_version` présentes
- `\d users` → structure de table conforme (colonnes, clé primaire, clé
  étrangère, index unique sur l'email)
- 3 rôles et 3 utilisateurs de test créés, mots de passe correctement hashés
  (jamais stockés en clair)

### Problèmes rencontrés et corrigés
- Docker Desktop ne démarrait pas → cause : version du noyau WSL2 obsolète,
  corrigé par `wsl --update` + redémarrage complet de la machine.
- Fichiers `.env`, `alembic.ini`, `script.py.mako`, `env.py` créés vides ou
  avec du contenu incorrect à plusieurs reprises → cause : les here-strings
  PowerShell (`@"..."@`) interprètent mal certains caractères spéciaux
  (`$`, `` ` ``) présents dans le contenu à écrire. Solution retenue : éditer
  ces fichiers directement dans VS Code plutôt que de les générer par script
  PowerShell.
- Incompatibilité entre `passlib` 1.7.4 et `bcrypt` 5.0.0 (erreur
  `AttributeError: module 'bcrypt' has no attribute '__about__'`) → corrigé en
  figeant `bcrypt==4.0.1` dans `requirements.txt`.

---

## Étape 2 — Authentification (JWT + RBAC)

### Objectif
Permettre à un utilisateur de se connecter et récupérer un jeton d'accès, puis
protéger les futures routes de l'API pour qu'elles ne soient accessibles
qu'aux utilisateurs authentifiés — avec un contrôle par rôle (RBAC) prêt à
l'emploi pour les prochaines étapes.

### Principe du JWT (résumé)
Un JWT (JSON Web Token) est un jeton signé numériquement, remis à
l'utilisateur une seule fois au login. Il contient son identité (email) et son
rôle, et une date d'expiration. Ce jeton est ensuite présenté à chaque requête
via le header HTTP `Authorization: Bearer <token>`. Le serveur peut vérifier
sa validité (signature + expiration) **sans consulter la base de données**
pour ça — seule la signature garantit que le jeton n'a pas été falsifié, via
une clé secrète (`JWT_SECRET_KEY`) connue uniquement du serveur.

### Ce qui a été fait

**1. `backend/app/core/security.py`**
- `hash_password()` / `verify_password()` — hashing et vérification de mot de
  passe via bcrypt (passlib)
- `create_access_token()` — génère un JWT signé contenant `sub` (email),
  `role`, et `exp` (expiration, configurée à 60 min par défaut)
- `decode_access_token()` — vérifie un jeton reçu ; retourne `None` s'il est
  invalide ou expiré, plutôt que de lever une exception brute

**2. `backend/app/schemas/user.py`**
- `LoginRequest` (email, password), `TokenResponse` (access_token, token_type),
  `UserResponse` (id, email, full_name, role) — formats de données validés
  automatiquement par FastAPI/Pydantic

**3. `backend/app/services/auth_service.py`**
- `authenticate_user()` — vérifie email + mot de passe contre la base ; ne
  distingue jamais "email inexistant" de "mot de passe incorrect" dans sa
  réponse, pour ne pas permettre à un attaquant de deviner quels comptes
  existent (bonne pratique de sécurité standard)
- `login()` — appelle `authenticate_user()` puis génère le token si succès

**4. `backend/app/api/v1/auth.py`**
- `POST /api/v1/auth/login` — reçoit email/password en JSON, retourne le JWT
- `GET /api/v1/auth/me` — route de test protégée, retourne les infos de
  l'utilisateur actuellement authentifié

**5. `backend/app/api/deps.py`**
- `get_current_user` — dependency FastAPI réutilisable sur n'importe quelle
  route : extrait le jeton du header `Authorization`, le décode, vérifie que
  l'utilisateur existe toujours et est actif. Utilise `HTTPBearer` (pas
  `OAuth2PasswordBearer`, qui suppose un flux de login par formulaire
  incompatible avec notre login en JSON).
- `require_role(*allowed_roles)` — factory de dependency pour restreindre une
  route à un ou plusieurs rôles (ex: `Depends(require_role("administrator"))`),
  prête à être utilisée sur les futures routes Admin/Cross-Domain.

**6. `backend/app/main.py`**
- Point d'entrée FastAPI ; importe explicitement `app.models` au démarrage
  pour que SQLAlchemy enregistre tous les modèles (`Role`, `User`) avant
  qu'aucune requête n'arrive — nécessaire pour que les relations entre
  classes (`User.role`) se résolvent correctement.

### Résultat vérifié (via l'interface Swagger `/docs`)

| Scénario | Résultat |
|---|---|
| `POST /auth/login` avec identifiants valides | `200 OK` + JWT retourné |
| `POST /auth/login` avec mauvais mot de passe | `401 Unauthorized` |
| `GET /auth/me` sans jeton | `401 Unauthorized` |
| `GET /auth/me` avec jeton valide | `200 OK` + infos utilisateur (`id`, `email`, `full_name`, `role`) |

### Problèmes rencontrés et corrigés
- Erreur `KeyError: 'Role'` au premier appel de l'API → SQLAlchemy ne trouvait
  pas la classe `Role` car elle n'était jamais importée au démarrage du
  serveur (seul `User` l'était, indirectement). Corrigé en créant
  `models/__init__.py` qui importe tous les modèles, puis en important ce
  module dans `main.py`.
- Interface Swagger affichant un formulaire `username`/`password` au lieu
  d'un simple champ pour coller le jeton → `OAuth2PasswordBearer` suppose un
  flux OAuth2 standard incompatible avec notre login en JSON. Remplacé par
  `HTTPBearer`, plus adapté.

---

## État actuel du projet

```
✅ Étape 1 — Fondations (Docker, PostgreSQL, modèles, migrations, seed)
✅ Étape 2 — Authentification (JWT, hashing bcrypt, route protégée, RBAC prêt)
⬜ Étape 3 — Persona Linux minimal (Orchestrator, LLM Router, premier chat)
⬜ Étape 4 — RAG (Knowledge CMS)
⬜ Étape 5 — MCP (Linux Server/Client)
⬜ Étape 6 — Duplication pour Storage
⬜ Étape 7 — Orchestrateur central + Cross-Domain
⬜ Étape 8 — Reports, Dashboard, Admin, Frontend
```

## Fichiers backend créés jusqu'ici

```
backend/
├── requirements.txt
├── .env                              (non versionné)
├── alembic.ini
├── alembic/env.py
├── alembic/script.py.mako
├── alembic/versions/<migration>.py
└── app/
    ├── main.py
    ├── core/
    │   ├── config.py
    │   └── security.py
    ├── database/
    │   ├── base.py
    │   ├── session.py
    │   └── seed.py
    ├── models/
    │   ├── __init__.py
    │   ├── role.py
    │   └── user.py
    ├── schemas/
    │   └── user.py
    ├── services/
    │   └── auth_service.py
    ├── api/
    │   ├── deps.py
    │   └── v1/
    │       └── auth.py
```

## Comment relancer le projet (pour le binôme)

```powershell
# 1. Démarrer Docker Desktop, puis :
docker compose up -d

# 2. Backend (dans un terminal, venv activé) :
cd backend
uvicorn app.main:app --reload

# 3. Tester sur http://127.0.0.1:8000/docs
#    Login avec linux@oasis.com / linux123 (ou storage@/admin@)
```

## Prochaine étape (Étape 3)

Construire un premier Persona (Linux) qui répond à une question via un LLM,
en passant par un composant "LLM Router" qui choisit le modèle selon la
complexité de la tâche (Llama 3.1 via Groq pour les cas simples, Claude pour
le raisonnement complexe) — sans encore brancher le RAG ni le MCP, pour
valider le mécanisme de bout en bout avant de le complexifier.

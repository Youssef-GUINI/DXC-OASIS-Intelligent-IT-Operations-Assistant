# OASIS AI Copilot — Rapport d'avancement (Étapes 3 & 4)

## Objectif de ce document

Ce rapport fait suite au rapport des étapes 1 et 2. Il détaille la construction
du premier Persona fonctionnel (Linux) et du système RAG (Knowledge CMS), pour
que le binôme comprenne le fonctionnement complet et puisse reprendre le
développement en connaissance de cause.

Rappel du plan global (8 étapes) :

```
✅ Étape 1 — Fondations (Docker, PostgreSQL, modèles, migrations, seed)
✅ Étape 2 — Authentification (JWT, hashing bcrypt, route protégée, RBAC prêt)
✅ Étape 3 — Persona Linux minimal (LLM Router, Groq, premier chat)
✅ Étape 4 — RAG (Knowledge CMS, ChromaDB, recherche sémantique)
⬜ Étape 5 — MCP (Linux Server/Client)
⬜ Étape 6 — Duplication pour Storage
⬜ Étape 7 — Orchestrateur central + Cross-Domain
⬜ Étape 8 — Reports, Dashboard, Admin, Frontend
```

---

## Étape 3 — Persona Linux minimal (LLM Router + premier chat)

### Objectif

Construire un premier chemin complet de bout en bout — de la question de
l'utilisateur jusqu'à une réponse générée par un vrai LLM — **sans encore
brancher le RAG ni le MCP**. L'idée : valider le mécanisme de routage avant
de le complexifier, plutôt que de tout construire en parallèle et devoir
déboguer plusieurs pièces à la fois.

### Principe du LLM Router

Décision actée dans l'architecture officielle (section 8) : **le Persona ne
choisit jamais lui-même un LLM**. Il délègue cette décision à un composant
central, le LLM Router, qui applique une règle simple (pas de classifieur IA,
pour rester réalisable en 2 mois) :

```
Tâche simple         → Llama 3.1/3.3 (via Groq, rapide et gratuit)
Raisonnement complexe → Claude (à brancher plus tard)
```

Avantage concret : si demain on change de fournisseur LLM ou qu'on ajoute un
troisième modèle, **aucun Persona n'a besoin d'être modifié** — ils
continuent tous à appeler `route()` de la même façon.

### Ce qui a été fait

**1. `backend/app/llm/groq_client.py`**
- Wrapper autour du SDK Python de Groq
- Expose une méthode `.chat(prompt)` qui envoie une requête au modèle Llama
  et retourne le texte de la réponse
- Lit la clé API et la configuration depuis `settings` (donc depuis `.env`,
  jamais codée en dur)

**2. `backend/app/orchestrator/llm_router.py`**
- `TaskComplexity` (Enum) : `SIMPLE` ou `COMPLEX` — évite les fautes de frappe
  qu'une chaîne de caractères libre permettrait
- `route(prompt, complexity)` : fonction unique appelée par tous les
  Personas ; aujourd'hui, redirige tout vers Groq ; la branche `COMPLEX` vers
  Claude est prête (lève une erreur explicite tant que la clé Anthropic n'est
  pas configurée, plutôt que d'échouer silencieusement)

**3. `backend/app/personas/base_persona.py`**
- Classe de base commune à tous les futurs Personas (Linux, Storage, etc.)
- `system_prompt` : le "rôle" que le LLM doit jouer — chaque Persona
  spécialisé le redéfinit avec ses propres responsabilités
- `build_prompt()` : assemble le prompt final envoyé au LLM
- `handle_message()` : point d'entrée unique — reçoit un message utilisateur,
  construit le prompt, appelle `route()`, retourne la réponse

**4. `backend/app/personas/linux/agent.py`**
- `LinuxPersona`, héritant de `BasePersona`
- `system_prompt` spécialisé : ingénieur système Linux expert en
  troubleshooting, CPU/RAM/disque, services système, diagnostic réseau
  (fidèle aux responsabilités définies section 3 de l'architecture)

**5. `backend/app/api/v1/linux.py`**
- `POST /api/v1/linux/chat` — reçoit `{"message": "..."}`, appelle
  `linux_persona.handle_message()`, retourne `{"response": "..."}`
- Protégée par JWT (`Depends(get_current_user)`) — réutilise directement le
  mécanisme construit à l'étape 2 ; aucun token valide = `401` avant même
  d'atteindre le Persona

### Schéma du flux (état à la fin de l'étape 3)

```
Utilisateur (avec JWT)
        │
        ▼
POST /api/v1/linux/chat
        │
        ▼
get_current_user (verification JWT)
        │
        ▼
LinuxPersona.handle_message()
        │
        ▼
LLM Router (route())
        │
        ▼
GroqClient
        │
        ▼
Llama 3.3 (API Groq)
        │
        ▼
Reponse renvoyee au frontend
```

### Résultat vérifié

| Test | Résultat |
|---|---|
| `POST /linux/chat` sans token | `401 Unauthorized` |
| `POST /linux/chat` avec token valide | `200 OK` + réponse technique cohérente |

### Problèmes rencontrés et corrigés

- `AttributeError: 'Settings' object has no attribute 'database_url'` /
  `'GROQ_API_KEY'` → causé par un refactor de `config.py` qui a changé la
  casse des attributs (majuscules ↔ minuscules) sans mettre à jour tous les
  fichiers qui utilisaient l'ancienne convention (`session.py`,
  `security.py`, `groq_client.py`). Décision retenue : tout garder en
  **minuscule** côté Python (`settings.database_url`), et retirer
  `case_sensitive=True` de la config Pydantic — les noms de variables dans
  `.env` peuvent rester en MAJUSCULES (convention standard des fichiers
  `.env`) sans que ça pose de conflit, car la correspondance entre `.env` et
  les attributs Python se fait alors sans tenir compte de la casse.
- Une clé API Groq a été partagée en clair dans la conversation de travail à
  deux reprises → **révoquée et remplacée immédiatement**. Règle retenue pour
  la suite : toute clé API se configure uniquement en éditant `.env`
  directement dans l'éditeur de code, jamais copiée dans un chat, un message,
  ou un canal non chiffré.

---

## Étape 4 — RAG (Knowledge CMS)

### Objectif

Donner au Persona Linux accès à de la documentation technique interne, pour
que ses réponses soient ancrées dans de vraies procédures plutôt que dans la
seule connaissance générale du LLM. C'est le composant "Knowledge CMS" prévu
section 9 de l'architecture officielle.

### Principe du RAG (Retrieval-Augmented Generation)

Le LLM ne "lit" pas une base de documents à chaque question — trop lent, trop
coûteux, et il faudrait lui envoyer des documents entiers alors que seule une
petite partie est pertinente. À la place, on utilise un pipeline en deux
temps :

**Indexation (une fois, à l'ajout de documents) :**
```
Document texte
      │
      ▼
Chunking (decoupage en morceaux ~500 mots, avec chevauchement)
      │
      ▼
Embedding (conversion de chaque morceau en vecteur numerique)
      │
      ▼
Stockage dans ChromaDB (base de donnees vectorielle)
```

**Recherche (à chaque question posée) :**
```
Question de l'utilisateur
      │
      ▼
Embedding de la question (meme modele que pour l'indexation)
      │
      ▼
Recherche par similarite dans ChromaDB
      │
      ▼
Les 3 chunks les plus proches semantiquement
      │
      ▼
Injectes dans le prompt envoye au LLM
```

**Ce qu'est un "embedding"** : une conversion de texte en une liste de
nombres (vecteur) qui capture le *sens* du texte, pas seulement les mots
utilisés. Deux phrases formulées différemment mais proches en sens auront des
vecteurs proches dans cet espace — c'est ce qui permet à ChromaDB de retrouver
un document pertinent même si la question ne reprend aucun mot exact du
document (recherche **sémantique**, pas recherche par mots-clés).

Le modèle d'embedding utilisé est **BAAI BGE Small** (décision de
l'architecture, section 9) — gratuit, tourne en local sur la machine, pas
d'appel API payant à chaque indexation/recherche.

### Ce qui a été fait

**1. `backend/app/rag/embedding_service.py`**
- `embed_text()` / `embed_texts()` — convertissent du texte en vecteurs via
  BGE Small
- Chargement "paresseux" (lazy loading) du modèle : il n'est chargé en
  mémoire qu'à la première utilisation réelle, pas à chaque import du module

**2. `backend/app/rag/chunker.py`**
- `chunk_text()` — découpe un texte long en morceaux de ~500 mots
- Chevauchement de 50 mots entre chunks consécutifs, pour éviter qu'une idée
  importante soit coupée en deux et perde son sens dans les deux morceaux

**3. `backend/app/rag/loader.py`**
- `load_directory()` — charge tous les fichiers `.txt`/`.md` d'un dossier
  (support PDF laissé pour une évolution future, pas bloquant pour le MVP)

**4. `backend/app/rag/vectorstore.py`**
- Pont vers ChromaDB (le conteneur Docker démarré à l'étape 1, sur le port
  `8001`)
- `add_chunks()` — indexe une liste de chunks dans une collection nommée
- `search()` — recherche les chunks les plus proches d'une requête, retourne
  aussi la distance (proximité sémantique) pour chaque résultat
- **Une collection par Persona** (`linux_kb`, puis `storage_kb` plus tard) —
  fidèle à la décision d'isolation des Personas de l'architecture officielle

**5. `backend/app/rag/indexing_pipeline.py`** et **`query_pipeline.py`**
- Assemblent les étapes précédentes en deux fonctions simples :
  `index_directory()` pour indexer tout un dossier de documents,
  `get_context_for_query()` pour récupérer le contexte pertinent à injecter
  dans un prompt

**6. Document de test indexé**
- `backend/app/rag/linux_kb/cpu_troubleshooting.md` — procédure de diagnostic
  CPU (commandes `top`, `htop`, `ps aux`, `mpstat`, vérification des tâches
  planifiées)

**7. Branchement dans le Persona (`base_persona.py` modifié)**
- Nouvel attribut `rag_collection` sur `BasePersona` — chaque Persona
  spécialisé le définit (`LinuxPersona.rag_collection = "linux_kb"`)
- `build_prompt()` récupère automatiquement le contexte pertinent via
  `get_context_for_query()` avant d'assembler le prompt final, et l'injecte
  avec une instruction explicite au LLM de s'en servir "quand il est
  pertinent" (pour éviter qu'il force une réponse basée sur un contexte qui
  ne correspondrait pas vraiment à la question)

### Schéma du flux (état à la fin de l'étape 4)

```
Utilisateur (avec JWT)
        │
        ▼
POST /api/v1/linux/chat
        │
        ▼
LinuxPersona.handle_message()
        │
        ▼
build_prompt()
        │
        ├──► get_context_for_query("linux_kb", question)
        │           │
        │           ▼
        │    Recherche semantique dans ChromaDB
        │           │
        │           ▼
        │    Chunks pertinents recuperes
        │
        ▼
Prompt final = system_prompt + contexte RAG + question
        │
        ▼
LLM Router → Groq → Llama 3.3
        │
        ▼
Reponse ancree dans la documentation interne
```

### Résultat vérifié

Test réalisé avec la question *"My CPU is always at 100%. What should I check
first?"* (formulée différemment du document source, en anglais alors que le
document est en français, pour bien prouver la recherche sémantique et pas
une simple recherche de mots-clés).

Réponse obtenue (`200 OK`) : le LLM a explicitement mentionné **"Selon la
documentation interne"**, puis repris fidèlement les commandes exactes du
document indexé (`top`, `htop`, `ps aux --sort=-%cpu | head -10`,
`mpstat -P ALL 1`, vérification de `crontab -l`) — preuve formelle que le
pipeline RAG fonctionne de bout en bout et que le LLM se base bien sur la
documentation fournie, pas uniquement sur sa connaissance générale.

### Problèmes rencontrés et corrigés

- `ModuleNotFoundError: No module named 'app.rag.chunker'` → le fichier
  n'avait pas été sauvegardé correctement lors de sa création dans
  l'éditeur. Recréé et vérifié avec `Get-Content` avant de continuer — la
  méthode de vérification systématique après chaque création de fichier
  (mise en place depuis l'étape 1) a permis d'identifier le problème
  rapidement.
- Premier lancement du script de test : téléchargement automatique du modèle
  BGE Small (~133 Mo) depuis Hugging Face — normal, comportement attendu au
  premier usage uniquement ; le modèle est ensuite mis en cache localement et
  les lancements suivants sont immédiats.

---

## État actuel du projet

```
✅ Étape 1 — Fondations (Docker, PostgreSQL, modèles, migrations, seed)
✅ Étape 2 — Authentification (JWT, hashing bcrypt, route protégée, RBAC prêt)
✅ Étape 3 — Persona Linux minimal (LLM Router, Groq, premier chat fonctionnel)
✅ Étape 4 — RAG (Knowledge CMS, ChromaDB, recherche semantique validee)
⬜ Étape 5 — MCP (Linux Server/Client)
⬜ Étape 6 — Duplication pour Storage
⬜ Étape 7 — Orchestrateur central + Cross-Domain
⬜ Étape 8 — Reports, Dashboard, Admin, Frontend
```

## Fichiers backend créés depuis le dernier rapport

```linux@oasis.com
backend/app/
├── llm/
│   └── groq_client.py
├── orchestrator/
│   └── llm_router.py
├── personas/
│   ├── base_persona.py
│   └── linux/
│       └── agent.py
├── api/v1/
│   └── linux.py
└── rag/
    ├── embedding_service.py
    ├── chunker.py
    ├── loader.py
    ├── vectorstore.py
    ├── indexing_pipeline.py
    ├── query_pipeline.py
    └── linux_kb/
        └── cpu_troubleshooting.md
```

## Identifiants de test (rappel)

| Email | Mot de passe | Rôle |
|---|---|---|
| `` | `linux123` | linux_engineer |
| `storage@oasis.com` | `storage123` | storage_engineer |
| `admin@oasis.com` | `admin123` | administrator |

## Comment tester le Persona Linux avec RAG (pour le binôme)

```powershell
# 1. Demarrer Docker Desktop, puis :
docker compose up -d

# 2. Backend (venv active) :
cd backend
uvicorn app.main:app --reload

# 3. Sur http://127.0.0.1:8000/docs :
#    - POST /auth/login avec linux@oasis.com / linux123 -> copier le token
#    - Authorize (cadenas en haut) -> coller le token
#    - POST /linux/chat avec {"message": "Mon CPU est bloque a 100%, que faire ?"}
```

## Prochaine étape (Étape 5)

Actuellement, le Persona Linux **parle** de commandes techniques (`top`,
`htop`...) mais ne les **exécute** jamais réellement — tout reste
conversationnel. L'étape 5 introduit le MCP (Model Context Protocol) : un
Linux MCP Client et un Linux MCP Server, distincts dans le code (fidèles au
schéma de l'architecture officielle) mais tournant dans le même process
FastAPI pour la V1 (décision de compromis validée précédemment). Le Server
exposera de premiers outils (au départ avec des données simulées) que le
Persona pourra appeler pour obtenir de vraies données système, avant d'écrire
son rapport.
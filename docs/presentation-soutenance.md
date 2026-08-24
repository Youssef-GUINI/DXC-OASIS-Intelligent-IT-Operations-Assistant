# DXC OASIS — Présentation de soutenance
**Kawthar Khayet — PFA DXC Technology**
Durée cible : 20 min de présentation + 10 min de questions · 21 slides + annexes

---

## Plan en un coup d'œil

| Partie | Slides | Temps | Message que le jury doit retenir |
|---|---|---|---|
| Contexte | 2–5 | 3 min | Le métier Storage & Backup perd du temps sur du diagnostic répétitif |
| Objectifs | 6–8 | 3 min | Un copilote utile *et* de confiance : 4 partis pris non négociables |
| Réalisations | 9–15 | 8 min | Une chaîne complète, du navigateur jusqu'à la commande Linux |
| Résultats | 16–18 | 4 min | Ça tourne sur une vraie VM, avec des chiffres et des limites assumées |
| Conclusion | 19–21 | 2 min | Ce que ça vaut, ce que j'ai appris, où ça va |

---

# PARTIE 1 — CONTEXTE

---

## Slide 1 — Page de titre

> # OASIS
> ## Transformer une conversation en actions vérifiées sur une infrastructure réelle
>
> **Intelligent IT Operations Assistant — Storage & Backup**
> Projet de Fin d'Année · DXC Technology
> Kawthar Khayet — Août 2026

**À dire (15 s) :** « Pendant ces six semaines, j'ai construit un copilote d'exploitation
pour les ingénieurs Storage & Backup. Sa particularité tient en une phrase que je vais
défendre pendant vingt minutes : il ne dit jamais rien qu'il n'ait vérifié lui-même sur
la machine. »

---

## Slide 2 — Sommaire : « De la question de l'ingénieur à la commande Linux »

1. **Contexte** — le quotidien d'un ingénieur Storage & Backup
2. **Objectifs** — pourquoi un chatbot ne suffisait pas
3. **Réalisations** — architecture, MCP, agent, boucle de confirmation
4. **Résultats** — démonstration, chiffres, limites
5. **Conclusion** — bilan et perspectives

---

## Slide 3 — « 3 h du matin, un job de sauvegarde tombe »

**Le déroulé d'un incident, aujourd'hui :**

- 03 h 12 — le timer `backup-luns.timer` échoue. Personne ne le voit.
- 09 h 00 — l'ingénieur arrive, ouvre 4 outils : supervision, console SAN, ITSM, wiki.
- 09 h 25 — il retrouve la commande `journalctl` dans un runbook PDF de 60 pages.
- 09 h 40 — il diagnostique : le dépôt de sauvegarde n'est plus initialisé.
- 09 h 50 — il corrige. Personne ne saura jamais *pourquoi* le ticket a été fermé.

> **Le problème n'est pas la difficulté technique. C'est la dispersion.**
> La connaissance est dans les têtes, les commandes dans l'historique bash,
> la traçabilité nulle part.

**À dire :** insister sur le dernier point — la perte de traçabilité est le vrai coût
pour DXC, pas les 40 minutes.

---

## Slide 4 — « L'IA générative promet beaucoup. Et c'est bien le problème. »

| Ce qu'un LLM sait faire | Ce qu'un exploitant exige |
|---|---|
| Produire une réponse plausible | Une donnée **exacte**, ou rien |
| Décrire une procédure générique | La procédure de **cette** machine |
| Enchaîner des actions | Ne **jamais** agir sans accord humain |
| Oublier le contexte | Une **trace opposable** de chaque geste |

> Un assistant qui invente un taux de remplissage à 74 % est pire qu'un écran vide :
> il détruit la confiance sur laquelle repose tout l'outil.

**À dire :** c'est LE slide qui justifie tous les choix techniques suivants. Le jury doit
comprendre ici que la contrainte du projet n'était pas « faire parler un LLM » mais
« empêcher un LLM de nuire ».

---

## Slide 5 — Le périmètre : « Un métier, une VM, zéro simulation »

- **Un persona métier :** Storage & Backup Engineer *(la persona Linux a été retirée
  pour privilégier la profondeur fonctionnelle plutôt que multiplier les vitrines)*
- **Une infrastructure réelle :** VM Ubuntu Server 24.04, pilotée en SSH
- **Un laboratoire reproductible :** 4 scripts shell qui recréent l'infra de démo
  sur une VM neuve en 3 commandes

| Composant d'entreprise | Équivalent monté dans la VM |
|---|---|
| Baie SAN + LUN | LVM sur disques loopback, `vg_prod`, volumes montés |
| NAS (NFS / SMB) | `nfs-kernel-server` + Samba |
| Stockage objet S3 | MinIO |
| Veeam / Commvault | `restic` piloté par timers systemd |
| Sauvegarde immuable anti-ransomware | MinIO Object Lock, mode COMPLIANCE |
| Snapshot / restauration de baie | `lvcreate --snapshot` / `lvconvert --merge` |

**À dire :** « Je n'ai pas simulé une baie de stockage dans du code Python. J'ai construit
les objets Linux équivalents, pour que l'application ait quelque chose de vrai à lire. »

---

# PARTIE 2 — OBJECTIFS

---

## Slide 6 — La problématique en une phrase

> ### Comment faire d'un modèle de langage un opérateur de confiance sur une infrastructure réelle —
> ### c'est-à-dire un système qui **lit le réel**, **propose** au lieu d'agir,
> ### et **prouve** ce qu'il avance ?

**À dire :** annoncer que la réponse tient en quatre partis pris, et que chacun est
vérifiable dans le code — c'est la promesse du slide suivant.

---

## Slide 7 — Quatre partis pris non négociables

**1 · Aucune donnée simulée**
Les outils exécutent réellement `df`, `lvs`, `systemctl`, `journalctl`, `/proc/diskstats`.
VM injoignable → erreur explicite affichée telle quelle. **Jamais de valeur de remplissage.**

**2 · Le modèle propose, l'humain décide**
Un outil qui modifie la VM n'est jamais exécuté par l'agent. Il écrit une ligne
`action_requests` au statut `pending`. Un seul chemin d'exécution existe :
`POST /storage/actions/{id}/confirm`.

**3 · Tout est audité**
Chaque appel d'outil → `mcp_calls` (arguments réels, résultat brut, corrélation).
Chaque requête HTTP → `audit_logs`. Chaque étape d'un incident → `incident_ticket_notes`.

**4 · La boucle se referme sur une vérification**
Un ticket n'est pas clos parce qu'une commande s'est bien terminée, mais parce que
**l'indicateur qui l'avait ouvert est redevenu sain**.

**À dire :** « Ces quatre règles ne sont pas des intentions de rapport : chacune
correspond à un module que je peux vous montrer dans le code. »

---

## Slide 8 — Les objectifs, traduits en fonctionnalités

| Objectif | Fonctionnalité livrée |
|---|---|
| Voir l'état réel sans se connecter à la VM | Dashboard KPI + graphique de performance |
| Interroger l'infrastructure en langage naturel | Chat avec agent Storage + tool calling |
| Ne plus rater un incident nocturne | Surveillance de fond, cycle de 300 s |
| Diagnostiquer sans chercher dans les runbooks | Investigation assistée + RAG |
| Agir sans risque | Proposition d'action + confirmation humaine |
| Capitaliser la connaissance | Data Hub : dépôt de documents indexés |
| Tracer et justifier | Audit complet + export de rapports PDF |

---

# PARTIE 3 — RÉALISATIONS

---

## Slide 9 — Architecture : « Sept étages, du navigateur au disque »

```
Ingénieur Storage (navigateur)
        │  HTTPS
Frontend React 18 + Vite + Tailwind          8 pages, JWT
        │  JSON + Bearer
API FastAPI  /api/v1                         11 routeurs, 43 endpoints
        │                                    ├── PostgreSQL 16 (SQLAlchemy)
Sécurité JWT HS256 + RBAC                    │
        │
StoragePersona (agent)  ←──────────────────→ Groq · gpt-oss-120b
        │  call_tool()                       ChromaDB (RAG)
MCP Client  ── stdio JSON-RPC ──►  MCP Server
        │
Tool Python (10 outils)
        │  paramiko
SSH ──► VM Ubuntu : df · lvs · systemctl · journalctl · restic · LVM
```

> **La formule à retenir :**
> `Utilisateur → React → FastAPI → Persona + Groq → MCP Client → MCP Server → Tool → SSH → VM`
> puis le résultat JSON remonte, est reformulé par le modèle, et s'affiche.

**À dire :** ne pas lire le schéma. Pointer les deux flèches latérales (Groq et ChromaDB)
et dire : « le modèle est une dépendance latérale, pas le cœur. Le cœur, c'est la colonne. »

---

## Slide 10 — MCP : « Donner des mains au modèle, pas les clés »

**Le Model Context Protocol** expose les capacités au LLM sans coder à la main un
catalogue de fonctions : le décorateur `mcp.tool()` dérive tout des annotations de
type et des docstrings. Le transport **stdio** isole les outils dans un processus séparé.

**10 outils, trois classes de risque — et c'est la classe qui commande le comportement :**

| Classe | Outils | Comportement |
|---|---|---|
| **Lecture** (6) | `get_capacity`, `list_backups`, `get_backup_job_status`, `get_backup_logs`, `list_snapshots`, `get_storage_health` | Exécution immédiate |
| **Remédiation** (3) | `run_backup`, `create_snapshot`, `repair_backup_repository` | → `action_requests` **pending** |
| **Destructif** (1) | `restore_from_backup` | → **pending** + avertissement rouge en interface |

**À dire :** « Le modèle voit les dix outils dans son catalogue. Mais lorsqu'il appelle
un outil de remédiation, ce qui s'exécute n'est pas l'outil : c'est l'enregistrement
d'une demande. Le modèle croit avoir agi. Il n'a fait que proposer. »

---

## Slide 11 — L'agent : « Répondre en s'appuyant sur trois sources »

À chaque question, le prompt de l'agent est assemblé à partir de :

1. **Le RAG** — les 3 passages les plus proches dans ChromaDB
   *Modèle E5 multilingue, asymétrique : préfixe `"query: "` sur la question,
   `"passage: "` sur le document. La base de connaissances est en anglais, les
   ingénieurs demandent en français — une fonction d'embedding unique serait
   nécessairement fausse d'un côté.*
2. **Le relevé MCP** — le résultat brut des outils appelés pendant le tour
3. **Le contexte métier** — numéro de ticket, cible technique, historique du fil

Puis : **tool calling Groq** (format OpenAI) → exécution des outils → second appel
pour reformuler en langage naturel → réponse affichée dans React.

> Choix de Groq : la **latence** — un ingénieur en incident n'attend pas — et le
> **tool calling natif**, qui permet de convertir le catalogue MCP en une seule fonction.

---

## Slide 12 — Le cœur du projet : les 9 temps de la confirmation humaine

```
1. ANALYSE       l'agent lit la VM et identifie la cause racine
2. PROPOSITION   action_requests(pending) — RIEN n'est exécuté
3. AFFICHAGE     phrase lisible + appel technique brut + alerte si destructif
4. DÉCISION      l'ingénieur clique « Confirm » ou « Reject »
5. DÉMARRAGE     démarrage du client MCP ; échec → HTTP 503, action toujours PENDING
6. EXÉCUTION     call_tool(action_type, confirm=True, **parameters) → SSH → VM
7. QUALIFICATION result contient "error" ? FAILED : COMPLETED — tracé dans mcp_calls
8. VÉRIFICATION  incident_verification.verify() relit l'indicateur sur la VM
9. CLÔTURE       verdict.resolved ? resolve_ticket + note : ticket ouvert avec la raison
```

**Ce que voit l'ingénieur avant de cliquer :**
> « Repair the backup repository configured for backup-luns »
> `repair_backup_repository(backup-luns)`
> ⚠ *This action overwrites existing data. Check the target before confirming.*

**À dire :** « Le rejet est traité comme une décision, pas comme un non-événement : il
écrit une note nommée, avec son motif, dans l'historique du ticket. »

---

## Slide 13 — « L'incident de 3 h du matin, cette fois »

**Le workflow automatique — aucun utilisateur impliqué :**

- **03 h 12** — la surveillance de fond (cycle 300 s, isolée en `asyncio.to_thread`)
  lit `systemctl list-timers` sur la VM
- Le job est `failed` → contrôle anti-doublon → **création automatique du ticket**
  Note : *« Detected automatically by monitoring: job … came back failed »*
- **09 h 00** — l'ingénieur ouvre le ticket, clique **« Investigate with OASIS »**
- L'agent appelle `get_backup_logs` puis `get_backup_job_status`, propose une
  remédiation, et remplit `root_cause` + `impact_summary` sur le ticket
- **09 h 02** — un clic. Exécution, vérification, clôture. **Tout est tracé.**

> **De 40 minutes de fouille à 2 minutes de décision** — et cette fois, l'historique
> du ticket explique pourquoi il a été fermé.

**À dire :** ce slide est la démonstration narrative du projet. Le faire coïncider avec
la démo live si le temps le permet.

---

## Slide 14 — Sous le capot : données, sécurité, traçabilité

**16 tables PostgreSQL, cinq familles, 14 migrations Alembic**

| Famille | Tables |
|---|---|
| Identité & sécurité | `roles`, `users`, `audit_logs`, `access_requests` |
| Incidents & actions | `incident_tickets`, `incident_ticket_notes`, `action_requests`, `mcp_calls` |
| Conversation | `chat_conversations`, `chat_messages` |
| Demandes de service | `service_requests`, `request_messages`, `request_events`, `request_attachments` |
| Connaissance & mesures | `knowledge_documents`, `disk_metrics` |

**Sécurité :** JWT HS256 · bcrypt · RBAC déclaratif par injection de dépendance
(`Depends(require_role(...))`). Le jeton porte le rôle, **mais le contrôle relit le rôle
en base** — une révocation prend effet immédiatement.

**Choix défendables :** SQLAlchemy synchrone (FastAPI exécute les routes `def` dans un
threadpool, ce qui convient exactement à du SSH bloquant) · JSONB pour conserver les
relevés bruts · `date_bin` PostgreSQL 14+ pour agréger le graphique de performance en
SQL plutôt qu'en Python.

---

## Slide 15 — L'interface : 8 pages pour un seul métier

- **Dashboard** — KPI, capacité, performance, bandeau d'attention, activité récente
- **Chat** — fils multiples, propositions d'action intégrées à la conversation
- **Incidents** — liste, fiche, investigation, notes horodatées
- **Requests** — demandes de service avec pièces jointes et journal d'événements
- **Data Hub** — dépôt de documents, statut d'indexation, motif d'échec affiché
- **Reports** — export PDF · **Search** — recherche globale · **Settings**

> **Le principe d'interface :** quand une donnée n'existe pas, l'écran le dit.
> Un document mal indexé affiche *pourquoi*. Une VM injoignable affiche l'erreur SSH.

---

# PARTIE 4 — RÉSULTATS

---

## Slide 16 — Le projet en chiffres

| | |
|---|---|
| **~15 800** lignes de code | 9 451 Python · 6 367 TypeScript / TSX |
| **43** endpoints REST | répartis en 11 routeurs sous `/api/v1` |
| **16** tables · **14** migrations | schéma versionné de bout en bout |
| **10** outils MCP | 6 lecture · 3 remédiation · 1 destructif |
| **12** workflows métier | de l'authentification à la collecte de métriques |
| **8** pages · **4** scripts de lab | SPA React + infra de démo reproductible |
| **6 semaines** | 10 juillet → 21 août 2026 |

**À dire :** ne pas s'attarder. Le seul chiffre à commenter est **10 outils / 3 classes** —
c'est le seul qui porte une idée, pas un volume.

---

## Slide 17 — Ce qui tourne réellement aujourd'hui

✅ Détection automatique d'un job de sauvegarde en échec, sans intervention humaine
✅ Diagnostic assisté par LLM appuyé sur des relevés SSH réels et sur le RAG
✅ Proposition → confirmation → exécution → **vérification** → clôture
✅ Audit intégral : `mcp_calls`, `audit_logs`, notes de ticket
✅ Indexation de documents et interrogation multilingue FR/EN
✅ Laboratoire rejouable sur une VM neuve en 3 commandes

**Démonstration live :** injection d'un incident → ticket automatique → investigation
→ confirmation → clôture vérifiée.

---

## Slide 18 — Limites assumées : « ce qui n'est pas fait, et je sais pourquoi »

| Limite | État réel | Pourquoi |
|---|---|---|
| Conteneurisation partielle | Docker fait tourner **PostgreSQL et ChromaDB** ; backend et frontend se lancent en local | La priorité a été la profondeur fonctionnelle, pas le packaging |
| `nginx.conf`, `ci.yml`, Dockerfiles | Présents mais **vides (0 octet)** | Prévus pour l'industrialisation, non entamés |
| Modules V1 morts | `base_persona.py`, `llm_router.py`, `rbac_middleware.py` compilent mais ne sont importés par personne | Vestiges de l'architecture multi-personas abandonnée |
| Persona Linux | Retirée | Un métier traité en profondeur plutôt que deux en surface |
| Fibre Channel, robots LTO | Non simulables sur une VM | L'équivalent honnête serait iSCSI + `targetcli` |

> **Pourquoi ce slide existe :** parce qu'un jury pose toujours la question
> « et ça, ça marche vraiment ? ». Autant y répondre avant qu'elle soit posée.

**À dire :** c'est le slide qui vous fait gagner en crédibilité. Le présenter avec
assurance, pas en s'excusant.

---

# PARTIE 5 — CONCLUSION

---

## Slide 19 — Ce que le projet démontre

**Techniquement** — qu'un LLM peut piloter une infrastructure réelle *à condition*
de l'encadrer : catalogue d'outils typé (MCP), classification par risque, point
d'exécution unique, vérification a posteriori.

**Méthodologiquement** — que la contrainte « aucune donnée simulée » n'est pas un
handicap de démonstration : c'est ce qui rend l'outil utilisable. Un blanc assumé
vaut mieux qu'un chiffre plausible.

**Pour DXC** — un socle transposable. Le persona Storage est une implémentation
parmi d'autres : la couche MCP, la boucle de confirmation et l'audit sont
indépendants du métier.

---

## Slide 20 — Compétences développées

| Domaine | Acquis concret |
|---|---|
| **IA appliquée** | RAG, embeddings asymétriques, tool calling, prompt engineering contraint |
| **Architecture** | Séparation agent / protocole / outils / infrastructure ; deux voies d'accès aux outils (MCP asynchrone quand un LLM est impliqué, appel direct sinon) |
| **Backend** | FastAPI, SQLAlchemy, Alembic, tâches de fond `lifespan`, sécurité JWT/RBAC |
| **Systèmes & stockage** | LVM, snapshots, timers systemd, restic, NFS/SMB, MinIO, immuabilité |
| **Rigueur d'ingénierie** | Documenter ce qui est mort comme mort, ce qui est vide comme vide |

---

## Slide 21 — Perspectives

**Court terme — industrialisation**
Compléter les Dockerfiles et la CI · reverse proxy nginx · tests automatisés

**Moyen terme — extension du périmètre**
Réactiver une seconde persona sur le socle existant · iSCSI + `targetcli` pour le
masquage de LUN · métriques historisées sur plusieurs semaines

**Long terme — la vraie question**
Passer d'un copilote qui **propose** à un système qui **exécute seul les remédiations
de classe faible**, une fois la confiance établie par l'historique. La donnée pour en
décider existe déjà : c'est le taux de confirmation par type d'action, lisible dans
`action_requests`.

> ### Merci — questions ?

---

# ANNEXE A — Questions probables du jury

**« Pourquoi MCP plutôt que d'écrire vos fonctions à la main ? »**
Parce que MCP dérive automatiquement le schéma JSON de chaque paramètre depuis les
annotations de type et les docstrings, et parce que le transport stdio isole les outils
dans un processus séparé. Écrire ce catalogue à la main, c'est le désynchroniser dès la
première signature modifiée.

**« Qu'est-ce qui empêche le modèle de contourner la confirmation ? »**
Rien dans le prompt — et c'est délibéré. Le garde-fou n'est pas une consigne, c'est une
structure : la fonction que l'agent appelle pour un outil de remédiation n'exécute pas
l'outil, elle écrit une ligne `pending`. Le seul code qui appelle réellement le tool avec
`confirm=True` est la route `/confirm`, protégée par RBAC.

**« Et si la VM répond faux, ou pas du tout ? »**
La commande SSH a un timeout de 5 s en connexion et 15 s en exécution. En cas d'échec,
l'outil remonte une erreur explicite, l'interface l'affiche telle quelle, et rien n'est
inventé. Pour l'exécution d'une action, un échec MCP renvoie un HTTP 503 et l'action
**reste** `pending` — elle n'est jamais marquée comme faite par défaut.

**« Pourquoi SQLAlchemy synchrone dans une application async ? »**
Une première version async échouait : sur une session synchrone, `db.commit()` renvoie
`None`, et `await None` lève un `TypeError`. Plutôt que de tout convertir, j'ai convergé
vers le synchrone — FastAPI compense en exécutant les routes `def` dans un threadpool,
ce qui est exactement le bon comportement pour du SSH bloquant.

**« Le dashboard n'apparaît pas dans `mcp_calls`. Pourquoi ? »**
Parce qu'il emprunte la voie directe : un `import` Python, sans LLM. La table `mcp_calls`
a un objectif précis — prouver qu'une réponse de l'agent s'appuie sur un relevé réel.
Y verser les lectures déterministes du dashboard la rendrait illisible.

**« Combien d'appels LLM par interaction ? »**
Un tour de chat = 2 appels Groq (sélection d'outils + reformulation) ; une investigation
= 3, le troisième produisant le JSON `root_cause` / `impact_summary`. La consommation est
suivie via le modèle `llm_usage`.

**« Pourquoi avoir retiré la persona Linux ? »**
Parce que deux personas superficielles n'auraient rien démontré. La valeur du projet est
dans la chaîne complète détection → diagnostic → proposition → confirmation → vérification,
et cette chaîne ne devient crédible qu'avec une infrastructure réelle derrière — que j'ai
construite pour un seul métier.

**« Que se passe-t-il si le modèle ne propose aucune action alors qu'il le devrait ? »**
Trois filets successifs : l'appel d'outil normal ; la récupération d'un appel écrit en
JSON dans la prose du modèle ; et à défaut, une action de repli déduite de la règle de
détection qui avait ouvert le ticket. Le cycle ne doit pas s'arrêter à l'avant-dernière
marche.

---

# ANNEXE B — Script de démonstration (5 min)

| # | Geste | Ce qu'on montre | Phrase |
|---|---|---|---|
| 1 | Dashboard | KPI et capacité réels | « Ces chiffres viennent de `df`, exécuté il y a quelques secondes. » |
| 2 | Terminal VM : injection d'incident | L'incident est provoqué pour de vrai | « Je casse le dépôt de sauvegarde. » |
| 3 | Attendre / forcer le cycle | Ticket créé seul | « Personne n'a rien saisi. » |
| 4 | Ouvrir le ticket | Note de détection automatique | « L'origine est horodatée et nommée. » |
| 5 | « Investigate with OASIS » | Cause racine + proposition | « Il a lu `journalctl`, il n'a pas deviné. » |
| 6 | Montrer la proposition **sans cliquer** | Statut `pending` | « À cet instant, rien n'a été exécuté. » |
| 7 | Confirm | Exécution + vérification + clôture | « Le ticket se ferme parce que l'indicateur est redevenu sain. » |
| 8 | Historique du ticket | Chaîne complète des notes | « Voilà ce qui manquait à 9 h 50. » |

**Plan de repli si la VM ne répond pas :** montrer l'erreur SSH affichée en clair —
« c'est exactement le comportement attendu, l'application ne comble pas le vide » —
puis dérouler sur des captures d'écran préparées.

# Checklist de l'étape 2
# 1. Démarrer les conteneurs Docker
# docker compose up -d

# Vérifier qu'ils tournent :

# docker ps

# Tu dois voir au minimum :

# oasis_postgres
# oasis_chromadb
# 2. Activer l'environnement virtuel
# .\.venv\Scripts\Activate.ps1
# 3. Lancer le backend

# Place-toi dans le dossier backend :

# cd backend

# Puis :

# uvicorn app.main:app --reload

# Tu dois voir :

# Application startup complete.
# 4. Ouvrir Swagger

# Dans ton navigateur :

# http://127.0.0.1:8000/docs

# Tu dois voir la documentation de l'API.

# 5. Tester le login

# Exécute :

# POST /api/v1/auth/login

# Avec :

# {
#   "email": "linux@oasis.com",
#   "password": "linux123"
# }

# Tu dois recevoir un access_token.

# 6. Tester une route protégée

# Clique sur Authorize dans Swagger.

# Colle :

# Bearer TON_TOKEN

# Puis teste :

# GET /api/v1/auth/me

# Tu dois obtenir :

# {
#   "id": 1,
#   "email": "linux@oasis.com",
#   "full_name": "Linux",
#   "role": "linux_engineer"
# }
# 7. Vérifier la base PostgreSQL
# docker exec -it oasis_postgres psql -U oasis_user -d oasis_db

# Puis :

# \dt

# Tu dois voir :

# users
# roles
# alembic_version
# 8. Quitter PostgreSQL
# \q
# Résultat attendu

# Si les 8 tests passent :

# ✅ Docker fonctionne
# ✅ PostgreSQL fonctionne
# ✅ ChromaDB fonctionne
# ✅ FastAPI fonctionne
# ✅ JWT fonctionne
# ✅ Authentification fonctionne
# ✅ Base de données fonctionne
# ✅ Étape 2 est toujours valide
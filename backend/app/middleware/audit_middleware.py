"""
Middleware HTTP global : journalise automatiquement CHAQUE requête reçue
par l'application (méthode, route, utilisateur si authentifié, code de
statut, durée), conformément au bloc "Audit Logging" de l'architecture
(Central Orchestrator + Admin Workspace).

Contrairement à une journalisation "à la carte" appelée manuellement route
par route, ce middleware capture tout automatiquement — y compris les
tentatives refusées par le RBAC (403) ou par l'authentification (401),
ce qui est précieux pour la supervision de sécurité.

Important : on ne journalise jamais le corps de la requête (donc jamais
un mot de passe en clair envoyé à /auth/login) — seulement des métadonnées
(méthode, route, statut, durée, IP).
"""
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.security import decode_access_token
from app.database.session import SessionLocal
from app.models.audit_log import AuditLog
from app.models.user import User

# Routes techniques qu'on ne veut pas polluer avec de l'audit (bruit sans
# valeur métier).
EXCLUDED_PATHS = {"/docs", "/openapi.json", "/redoc", "/favicon.ico"}


def _extract_user_id(request: Request, db) -> int | None:
    """
    Décode le JWT présent dans l'en-tête Authorization, si présent,
    et retrouve l'id utilisateur correspondant (le token contient l'email,
    pas directement l'id — même convention que get_current_user).
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header.removeprefix("Bearer ").strip()
    payload = decode_access_token(token)
    if payload is None:
        return None

    email = payload.get("sub")
    if email is None:
        return None

    user = db.query(User).filter(User.email == email).first()
    return user.id if user else None


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        start_time = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start_time) * 1000)

        db = SessionLocal()
        try:
            user_id = _extract_user_id(request, db)
            entry = AuditLog(
                user_id=user_id,
                action=request.method,
                resource=request.url.path,
                details={
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "client_ip": request.client.host if request.client else None,
                },
            )
            db.add(entry)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

        return response
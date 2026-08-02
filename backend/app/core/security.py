from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": subject,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None
"""
À AJOUTER dans backend/app/core/security.py (ne remplace pas le fichier,
juste ajouter cette fonction à la suite des fonctions existantes).

Nécessite les mêmes imports déjà présents : jwt, datetime, timedelta, settings.
Si "timezone" n'est pas déjà importé depuis datetime, l'ajouter aussi.
"""


def create_cross_domain_token(subject: str, workspace: str, minutes: int = 30) -> str:
    """
    Crée un JWT à portée limitée : accès en lecture seule à UN SEUL
    workspace précis, avec une expiration courte — conformément au bloc
    "Temporary Read-Only Token (Scope + Expiration)" de l'architecture.

    Différent de create_access_token (token de connexion classique) :
    celui-ci porte un "scope" et un "workspace" explicites, que le futur
    MCP Client devra vérifier avant d'accepter une requête cross-domain.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)

    payload = {
        "sub": subject,
        "scope": "cross_domain_read_only",
        "workspace": workspace,
        "exp": expire,
    }

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
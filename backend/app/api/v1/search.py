"""
app/api/v1/search.py

Recherche globale de la barre du haut.

La route est volontairement unique : l'ingénieur tape un mot, il veut voir
d'un coup l'incident, la demande, la conversation ou le document qui
correspond -- pas choisir d'abord dans quelle catégorie chercher.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.user import User
from app.schemas.search import SearchHitOut
from app.services import search_service

router = APIRouter(prefix="/storage/search", tags=["search"])


@router.get("", response_model=list[SearchHitOut])
def search(
    q: str = Query("", max_length=200),
    limit: int = Query(search_service.DEFAULT_LIMIT_PER_TYPE, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("storage_engineer", "administrator")),
):
    hits = search_service.search(db, current_user, q, limit_per_type=limit)
    return [SearchHitOut.model_validate(hit) for hit in hits]

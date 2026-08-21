"""Schémas de la recherche globale."""

from datetime import datetime

from pydantic import BaseModel


class SearchHitOut(BaseModel):
    """
    Un résultat, indépendant des routes de l'interface.

    `type` dit ce que c'est (incident, request, conversation, document) et
    `id` comment l'ouvrir -- le frontend en déduit la page à afficher.
    """

    type: str
    id: str
    title: str
    subtitle: str | None
    timestamp: datetime | None

    class Config:
        from_attributes = True

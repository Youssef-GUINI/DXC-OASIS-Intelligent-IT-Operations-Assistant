"""
app/rag/embedding_service.py

Vectorisation des textes du RAG.

Le modele est multilingue : la base de connaissances Storage est en anglais
(NetApp, Veeam, TrueNAS, AWS) alors que les ingenieurs posent leurs questions
en francais, et les documents deposes dans le Data Hub peuvent etre dans l'une
ou l'autre langue. Un modele anglophone comme bge-small-en-v1.5 place ces deux
langues dans des regions eloignees de l'espace vectoriel : la question ne
retrouve pas le passage qui y repond.

Les modeles de la famille E5 sont *asymetriques* : ils ont ete entraines avec
un prefixe "query: " devant la question et "passage: " devant le document
indexe. Omettre ces prefixes degrade nettement la pertinence, d'ou la
separation stricte entre embed_query() et embed_passages() -- une fonction
unique embed() serait forcement fausse d'un cote ou de l'autre.
"""

from __future__ import annotations

from sentence_transformers import SentenceTransformer

from app.core.config import settings

_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    """Charge le modele une seule fois par processus (plusieurs centaines de Mo)."""
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.embedding_model)
    return _model


def embed_query(text: str) -> list[float]:
    """Vectorise une question posee par l'utilisateur."""
    model = get_embedding_model()
    prefixed = f"{settings.embedding_query_prefix}{text}"
    return model.encode(prefixed, normalize_embeddings=True).tolist()


def embed_passages(texts: list[str]) -> list[list[float]]:
    """Vectorise des chunks destines a etre indexes."""
    if not texts:
        return []
    model = get_embedding_model()
    prefixed = [f"{settings.embedding_passage_prefix}{text}" for text in texts]
    return model.encode(prefixed, normalize_embeddings=True).tolist()

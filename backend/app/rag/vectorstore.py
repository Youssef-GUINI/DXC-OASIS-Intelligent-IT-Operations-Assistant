"""
app/rag/vectorstore.py

Acces a Chroma : creation des collections, ecriture des chunks, recherche.

Toutes les collections passent par get_or_create_collection(), qui refuse une
collection construite avec un autre modele d'embedding que celui configure.
Ce garde-fou n'est pas cosmetique : multilingual-e5-small produit des vecteurs
de 384 dimensions, exactement comme l'ancien bge-small-en-v1.5. Chroma
accepterait donc la requete sans la moindre erreur et renverrait des voisins
calcules dans deux espaces vectoriels incompatibles -- des reponses fausses,
mais parfaitement plausibles. Mieux vaut un echec explicite.
"""

from __future__ import annotations

import chromadb

from app.core.config import settings
from app.rag.embedding_service import embed_passages, embed_query

_MODEL_METADATA_KEY = "embedding_model"


class EmbeddingModelMismatch(RuntimeError):
    """La collection a ete indexee avec un autre modele d'embedding."""


def get_chroma_client():
    return chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)


def get_or_create_collection(name: str):
    client = get_chroma_client()
    # A la creation, le modele courant est grave dans les metadonnees. Sur une
    # collection existante, Chroma ignore ce parametre et renvoie les
    # metadonnees d'origine : c'est exactement ce qu'on veut comparer.
    collection = client.get_or_create_collection(
        name=name,
        metadata={_MODEL_METADATA_KEY: settings.embedding_model},
    )

    indexed_with = (collection.metadata or {}).get(_MODEL_METADATA_KEY)
    if indexed_with != settings.embedding_model:
        raise EmbeddingModelMismatch(
            f"La collection '{name}' a ete indexee avec "
            f"{indexed_with or 'un modele inconnu (anterieur au suivi de version)'}, "
            f"or la configuration demande {settings.embedding_model}. "
            f"Les vecteurs ne sont pas comparables. "
            f"Reconstruisez l'index : python -m app.rag.reindex"
        )
    return collection


def add_chunks(collection_name: str, chunks: list[str], source: str):
    collection = get_or_create_collection(collection_name)
    embeddings = embed_passages(chunks)
    ids = [f"{source}_{i}" for i in range(len(chunks))]
    metadatas = [{"source": source, "chunk_index": i} for i in range(len(chunks))]

    # upsert rend l'indexation relancable : un document deja indexe est mis a
    # jour au lieu de provoquer une erreur d'identifiant duplique.
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )


def search(collection_name: str, query: str, n_results: int = 3) -> list[dict]:
    collection = get_or_create_collection(collection_name)
    query_embedding = embed_query(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
    )

    output = []
    for doc, metadata, distance in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        output.append({"text": doc, "source": metadata["source"], "distance": distance})
    return output

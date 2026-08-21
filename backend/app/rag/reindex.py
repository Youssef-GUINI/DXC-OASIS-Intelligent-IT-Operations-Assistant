"""
app/rag/reindex.py

Reconstruit integralement la collection RAG apres un changement de modele
d'embedding.

    cd backend
    python -m app.rag.reindex

Pourquoi une reconstruction complete, et non une mise a jour : les vecteurs
deja presents ont ete calcules par l'ancien modele. Comme multilingual-e5-small
produit des vecteurs de la meme dimension que bge-small-en-v1.5 (384), Chroma
ne signalerait aucune erreur -- il renverrait simplement des voisins faux. La
collection est donc supprimee, puis reconstruite depuis les sources.

Deux sources alimentent 'storage_kb' :
  1. les .md versionnes dans app/rag/storage_kb/ ;
  2. les documents deposes par les ingenieurs dans le Data Hub, dont le
     fichier d'origine est conserve sous uploads/.
"""

from __future__ import annotations

from app.core.config import settings
from app.database.session import SessionLocal
from app.rag.indexing_pipeline import index_directory
from app.rag.vectorstore import get_chroma_client
from app.services import knowledge_service

COLLECTION = "storage_kb"
KB_DIRECTORY = "app/rag/storage_kb"


def drop_collection(name: str) -> None:
    client = get_chroma_client()
    try:
        client.delete_collection(name)
        print(f"Collection '{name}' supprimee.")
    except Exception as error:  # noqa: BLE001 -- collection absente au premier passage
        print(f"Collection '{name}' non supprimee ({error}).")


def reindex_datahub_documents(collection: str) -> int:
    """Re-vectorise les documents du Data Hub. Retourne le nombre d'echecs."""
    db = SessionLocal()
    failures = 0
    try:
        documents = knowledge_service.list_documents(db, collection=collection)
        if not documents:
            print("  aucun document Data Hub a reindexer.")
            return 0

        for document in documents:
            refreshed = knowledge_service.reindex_document(db, document)
            print(
                f"  {refreshed.filename} -> {refreshed.chunk_count} chunks "
                f"({refreshed.status.value})"
            )
            if refreshed.error:
                failures += 1
                print(f"     echec : {refreshed.error}")
    finally:
        db.close()
    return failures


def main() -> None:
    print(f"Modele d'embedding : {settings.embedding_model}")
    print(f"Prefixes           : query={settings.embedding_query_prefix!r} "
          f"passage={settings.embedding_passage_prefix!r}\n")

    drop_collection(COLLECTION)

    print(f"\nIndexation de {KB_DIRECTORY} ...")
    index_directory(KB_DIRECTORY, collection_name=COLLECTION)

    print("\nReindexation des documents Data Hub ...")
    failures = reindex_datahub_documents(COLLECTION)

    if failures:
        print(f"\nTermine avec {failures} document(s) en echec.")
    else:
        print("\nTermine.")


if __name__ == "__main__":
    main()

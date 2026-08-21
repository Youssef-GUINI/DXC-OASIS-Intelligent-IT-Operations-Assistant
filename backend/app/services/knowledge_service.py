"""
app/services/knowledge_service.py

Data Hub : réception d'un document envoyé par l'ingénieur, indexation dans
la collection Chroma que la persona Storage interroge, et suppression.

Le nom de fichier fourni par le client n'est jamais utilisé pour construire
un chemin — le fichier est stocké sous un UUID, ce qui rend toute traversée
de répertoire impossible. Le nom d'origine ne survit que comme métadonnée.

Le fichier brut est conservé sur disque après indexation : c'est ce qui rend
`reindex_document` possible, et donc ce qui permet de changer de modèle
d'embedding sans redemander leurs documents aux ingénieurs.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.knowledge_document import DocumentStatus, KnowledgeDocument
from app.rag.chunker import chunk_text
from app.rag.embedding_service import embed_passages
from app.rag.vectorstore import get_or_create_collection

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
TEXT_EXTENSIONS = {".md", ".txt", ".log", ".json", ".yaml", ".yml", ".csv"}
ALLOWED_EXTENSIONS = TEXT_EXTENSIONS | {".pdf"}

# En dessous de ce nombre de mots (hors titres Markdown), un document n'apporte
# rien au RAG. Le cas typique est le PDF scanne : pypdf n'y trouve aucune couche
# texte, le convertisseur ne produit que l'en-tete "# nom_du_fichier.pdf", et le
# document etait jusqu'ici marque INDEXED alors qu'il ne contenait rien.
MIN_INDEXABLE_WORDS = 20


class DocumentError(ValueError):
    """Refus métier (format, taille, document introuvable)."""


def _upload_dir() -> Path:
    directory = Path(settings.upload_dir)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _extract_text(raw: bytes, extension: str, title: str) -> str:
    if extension == ".pdf":
        from app.rag.documentation.converters.pdf_to_md import convert

        return convert(raw, title=title)
    return raw.decode("utf-8", errors="replace")


def _chroma_source(document_id: uuid.UUID) -> str:
    """Préfixe des ids Chroma — permet de retrouver les chunks à la suppression."""
    return f"datahub:{document_id}"


def _body_word_count(text: str) -> int:
    """
    Compte les mots du corps, en ignorant les titres Markdown.

    pdf_to_md.convert prefixe systematiquement le document d'un "# titre" et
    chaque page d'un "## Page N". Compter le texte brut ferait donc passer un
    PDF sans couche texte pour un document non vide.
    """
    body = [line for line in text.splitlines() if not line.lstrip().startswith("#")]
    return len(" ".join(body).split())


def _chunk_ids(document_id: uuid.UUID, count: int) -> list[str]:
    source = _chroma_source(document_id)
    return [f"{source}_{index}" for index in range(count)]


def _drop_chunks(document: KnowledgeDocument) -> None:
    """Retire de Chroma les chunks d'une indexation précédente."""
    if not document.chunk_count:
        return
    get_or_create_collection(document.collection).delete(
        ids=_chunk_ids(document.id, document.chunk_count),
    )


def _index_document(document: KnowledgeDocument, text: str) -> int:
    """Découpe, vectorise et pousse le texte dans Chroma. Retourne le nombre de chunks."""
    words = _body_word_count(text)
    if words < MIN_INDEXABLE_WORDS:
        raise DocumentError(
            f"Le document ne contient pas assez de texte exploitable "
            f"({words} mot(s) hors titres, minimum {MIN_INDEXABLE_WORDS}). "
            f"S'il s'agit d'un PDF scanné ou d'une image exportée en PDF, il n'a pas "
            f"de couche texte : il faut lui appliquer un OCR avant de le déposer."
        )

    chunks = [chunk for chunk in chunk_text(text) if chunk.strip()]
    if not chunks:
        raise DocumentError("Aucun texte exploitable n'a pu être extrait du document.")

    chroma = get_or_create_collection(document.collection)
    # Mêmes embeddings que vectorstore.add_chunks : la collection storage_kb
    # doit rester dans un espace vectoriel homogène.
    chroma.upsert(
        ids=_chunk_ids(document.id, len(chunks)),
        embeddings=embed_passages(chunks),
        documents=chunks,
        metadatas=[
            {"source": document.filename, "document_id": str(document.id), "chunk_index": index}
            for index in range(len(chunks))
        ],
    )
    return len(chunks)


def create_document(
    db: Session,
    *,
    filename: str,
    content_type: str | None,
    raw: bytes,
    user_id: int,
    collection: str = "storage_kb",
) -> KnowledgeDocument:
    if not raw:
        raise DocumentError("Le fichier est vide.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise DocumentError(
            f"Fichier trop volumineux ({len(raw) // 1024} Ko). Limite : "
            f"{MAX_UPLOAD_BYTES // (1024 * 1024)} Mo."
        )

    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise DocumentError(
            f"Format '{extension or 'inconnu'}' non pris en charge. "
            f"Formats acceptés : {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )

    document_id = uuid.uuid4()
    stored_path = _upload_dir() / f"{document_id}{extension}"
    stored_path.write_bytes(raw)

    document = KnowledgeDocument(
        id=document_id,
        filename=Path(filename).name,
        stored_path=str(stored_path),
        content_type=content_type,
        size_bytes=len(raw),
        collection=collection,
        uploaded_by=user_id,
        status=DocumentStatus.PENDING,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        text = _extract_text(raw, extension, document.filename)
        document.chunk_count = _index_document(document, text)
        document.status = DocumentStatus.INDEXED
        document.indexed_at = datetime.now(timezone.utc)
    except Exception as error:  # noqa: BLE001 -- Chroma indisponible, PDF illisible, etc.
        document.status = DocumentStatus.FAILED
        document.error = str(error)[:500]

    db.commit()
    db.refresh(document)
    return document


def reindex_document(db: Session, document: KnowledgeDocument) -> KnowledgeDocument:
    """
    Re-vectorise un document déjà stocké, à partir du fichier conservé sur
    disque. Utilisé après un changement de modèle d'embedding, et pour
    rattraper un document resté en FAILED.

    Les chunks de l'indexation précédente sont retirés d'abord : si le nouveau
    découpage en produit moins, les anciens resteraient sinon dans la
    collection sans que rien ne les référence.
    """
    try:
        text = read_document_text(document)
        _drop_chunks(document)
        document.chunk_count = _index_document(document, text)
        document.status = DocumentStatus.INDEXED
        document.indexed_at = datetime.now(timezone.utc)
        document.error = None
    except Exception as error:  # noqa: BLE001 -- fichier disparu, Chroma indisponible, etc.
        document.status = DocumentStatus.FAILED
        document.error = str(error)[:500]

    db.commit()
    db.refresh(document)
    return document


def list_documents(db: Session, *, collection: str = "storage_kb") -> list[KnowledgeDocument]:
    return (
        db.query(KnowledgeDocument)
        .filter(KnowledgeDocument.collection == collection)
        .order_by(KnowledgeDocument.created_at.desc())
        .all()
    )


def get_document(db: Session, document_id: uuid.UUID) -> KnowledgeDocument:
    document = db.get(KnowledgeDocument, document_id)
    if document is None:
        raise DocumentError("Document introuvable.")
    return document


def read_document_text(document: KnowledgeDocument) -> str:
    path = Path(document.stored_path)
    if not path.exists():
        raise DocumentError("Le fichier n'est plus présent sur le serveur.")
    return _extract_text(path.read_bytes(), path.suffix.lower(), document.filename)


def delete_document(db: Session, document_id: uuid.UUID) -> None:
    document = get_document(db, document_id)

    try:
        _drop_chunks(document)
    except Exception:  # noqa: BLE001 -- Chroma indisponible : on retire quand même le document
        pass

    Path(document.stored_path).unlink(missing_ok=True)
    db.delete(document)
    db.commit()

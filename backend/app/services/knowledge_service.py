import os
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.knowledge_document import KnowledgeDocument
from app.rag.indexing_pipeline import index_uploaded_file
from app.rag.loader import load_any_file
from app.rag.vectorstore import delete_by_source

UPLOAD_DIR = "app/rag/linux_kb"


def save_and_index_document(
    db: Session, filename: str, file_bytes: bytes, content_type: str | None, user_id: int
) -> KnowledgeDocument:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(file_bytes)

    doc = KnowledgeDocument(
        filename=filename,
        content_type=content_type,
        collection="linux_kb",
        size_bytes=len(file_bytes),
        uploaded_by_id=user_id,
    )

    try:
        chunk_count = index_uploaded_file(filepath, filename, collection_name="linux_kb")
        doc.chunk_count = chunk_count
        doc.status = "indexed"
        doc.indexed_at = datetime.now(timezone.utc)
    except Exception as exc:
        doc.chunk_count = 0
        doc.status = "failed"
        doc.error = str(exc)

    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def list_documents(db: Session) -> list[KnowledgeDocument]:
    return db.query(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc()).all()


def get_document_content(db: Session, document_id: int) -> dict | None:
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == document_id).first()
    if not doc:
        return None
    filepath = os.path.join(UPLOAD_DIR, doc.filename)
    if not os.path.exists(filepath):
        return {"filename": doc.filename, "text": "[Fichier introuvable sur le disque]"}
    text = load_any_file(filepath)
    return {"filename": doc.filename, "text": text}


def delete_document(db: Session, document_id: int) -> bool:
    doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == document_id).first()
    if not doc:
        return False

    delete_by_source(doc.collection, doc.filename)

    filepath = os.path.join(UPLOAD_DIR, doc.filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    db.delete(doc)
    db.commit()
    return True
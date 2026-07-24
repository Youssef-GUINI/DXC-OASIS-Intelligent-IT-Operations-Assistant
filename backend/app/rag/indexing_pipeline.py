from app.rag.loader import load_directory
from app.rag.chunker import chunk_text
from app.rag.vectorstore import add_chunks


def index_directory(directory: str, collection_name: str):
    docs = load_directory(directory)
    if not docs:
        print(f"Aucun document trouve dans {directory}")
        return

    for filename, content in docs.items():
        chunks = chunk_text(content)
        add_chunks(collection_name, chunks, source=filename)
        print(f"{filename} -> {len(chunks)} chunks indexes dans '{collection_name}'")
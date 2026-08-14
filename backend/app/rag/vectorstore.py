import chromadb

from app.core.config import settings
from app.rag.embedding_service import embed_text, embed_texts


def get_chroma_client():
    return chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)


def get_or_create_collection(name: str):
    client = get_chroma_client()
    return client.get_or_create_collection(name=name)


def add_chunks(collection_name: str, chunks: list[str], source: str):
    collection = get_or_create_collection(collection_name)
    embeddings = embed_texts(chunks)
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
    query_embedding = embed_text(query)

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


from app.rag.vectorstore import search


def get_context_for_query(collection_name: str, query: str, n_results: int = 3) -> str:
    results = search(collection_name, query, n_results=n_results)
    if not results:
        return ""

    context_parts = []
    for r in results:
        context_parts.append(f"[Source: {r['source']}]\n{r['text']}")

    return "\n\n---\n\n".join(context_parts)
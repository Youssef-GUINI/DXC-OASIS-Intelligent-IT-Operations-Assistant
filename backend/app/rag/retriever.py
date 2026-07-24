from app.rag.query_pipeline import get_context_for_query


class Retriever:
    """
    Point d'entrée unique du RAG.
    Les Personas utilisent cette classe pour récupérer
    le contexte depuis la Knowledge Base.
    """

    def retrieve(
        self,
        collection_name: str,
        question: str,
        n_results: int = 3,
    ) -> str:
        return get_context_for_query(
            collection_name=collection_name,
            query=question,
            n_results=n_results,
        )


retriever = Retriever()
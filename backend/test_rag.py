from app.rag.indexing_pipeline import index_directory
from app.rag.query_pipeline import get_context_for_query

# Indexation
index_directory("app/rag/linux_kb", collection_name="linux_kb")

# Recherche
context = get_context_for_query("linux_kb", "mon serveur a un CPU bloque a 100%")
print("=== CONTEXTE RECUPERE ===")
print(context)
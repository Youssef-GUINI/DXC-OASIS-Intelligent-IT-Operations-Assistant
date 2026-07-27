from app.rag.query_pipeline import get_context_for_query


question = "Le job de sauvegarde echoue avec le code E-BKP-042. Que faut-il verifier ?"
context = get_context_for_query("storage_kb", question)

print("=== CONTEXTE STORAGE RECUPERE ===")
print(context)

from app.rag.retriever import retriever

context = retriever.retrieve(
    collection_name="linux_kb",
    question="How can I diagnose a CPU issue on Linux?"
)

print("===== CONTEXT =====")
print(context)
from app.rag.vectorstore import get_or_create_collection

collection = get_or_create_collection("linux_kb")
all_data = collection.get()

print("Nombre total de chunks dans linux_kb :", len(all_data["ids"]))
print()

for chunk_id, doc in zip(all_data["ids"], all_data["documents"]):
    print(f"{chunk_id} — {doc[:80]}...")
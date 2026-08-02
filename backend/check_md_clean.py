from pathlib import Path

JUNK_MARKERS = [
    "Community Forum", "Discord", "Suggest changes",
    "Send us an email", "Creating your file", "Cancel",
    "Your file is ready", "double_arrow", "GitHub issue",
]

kb_path = Path("app/rag/storage_kb")

for md_file in kb_path.glob("*.md"):
    content = md_file.read_text(encoding="utf-8")
    found = [marker for marker in JUNK_MARKERS if marker in content]
    if found:
        print(f"❌ {md_file.name} contient encore : {found}")
    else:
        print(f"✅ {md_file.name} est propre")
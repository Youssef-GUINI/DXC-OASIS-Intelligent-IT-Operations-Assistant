"""
Applique le nettoyage à tous les fichiers .md déjà présents dans un
dossier de knowledge base (storage_kb, linux_kb...), en place.

Usage :
    python clean_existing_files.py ../storage_kb
    python clean_existing_files.py ../linux_kb
"""
import sys
from pathlib import Path

from converters import clean_markdown


def main(folder: str) -> None:
    kb_path = Path(folder)
    if not kb_path.is_dir():
        print(f"Dossier introuvable : {kb_path}")
        return

    for md_file in kb_path.glob("*.md"):
        original = md_file.read_text(encoding="utf-8")
        cleaned = clean_markdown.clean(original)

        if cleaned == original:
            print(f"  = {md_file.name} (déjà propre, rien à faire)")
            continue

        md_file.write_text(cleaned, encoding="utf-8")
        removed_chars = len(original) - len(cleaned)
        print(f"  ✅ {md_file.name} — {removed_chars} caractères de bruit retirés")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage : python clean_existing_files.py <dossier_kb>")
        sys.exit(1)

    main(sys.argv[1])

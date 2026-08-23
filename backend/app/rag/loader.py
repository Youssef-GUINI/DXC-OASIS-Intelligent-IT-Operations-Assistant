from pathlib import Path

from pypdf import PdfReader


def load_text_file(filepath: str) -> str:
    return Path(filepath).read_text(encoding="utf-8")


def load_directory(directory: str) -> dict[str, str]:
    """
    Charge tous les fichiers .txt et .md d'un dossier.
    Retourne un dict {nom_fichier: contenu}.
    """
    docs = {}
    for path in Path(directory).glob("*"):
        if path.suffix in (".txt", ".md"):
            docs[path.name] = load_text_file(str(path))
    return docs


def load_pdf_file(filepath: str) -> str:
    reader = PdfReader(filepath)
    text_parts = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(text_parts)


def load_any_file(filepath: str) -> str:
    """
    Charge le contenu texte d'un fichier, quel que soit son type
    (.md, .txt, .pdf) - point d'entree unique pour l'upload.
    """
    if filepath.lower().endswith(".pdf"):
        return load_pdf_file(filepath)
    return load_text_file(filepath)
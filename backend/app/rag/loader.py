from pathlib import Path


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
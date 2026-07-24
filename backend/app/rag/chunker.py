def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Decoupe un texte en morceaux de ~chunk_size mots, avec un
    chevauchement (overlap) pour eviter de couper une idee en deux
    morceaux qui perdraient leur contexte.
    """
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks
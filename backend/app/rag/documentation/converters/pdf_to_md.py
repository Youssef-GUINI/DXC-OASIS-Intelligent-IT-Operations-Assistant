"""
Convertit un PDF en Markdown basique. Extraction de texte simple (pas de
préservation fine de mise en page) — suffisant pour un document technique
de type SOP/guide, où le contenu textuel importe plus que le formatting.
"""
from io import BytesIO

from pypdf import PdfReader


def convert(pdf_bytes: bytes, title: str | None = None) -> str:
    """
    Convertit le contenu binaire d'un PDF en texte Markdown.

    - title : titre optionnel à ajouter en en-tête du document généré.
    """
    reader = PdfReader(BytesIO(pdf_bytes))

    parts = []
    if title:
        parts.append(f"# {title}\n")

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if not text:
            continue
        parts.append(f"## Page {page_number}\n\n{text}\n")

    return "\n".join(parts).strip()
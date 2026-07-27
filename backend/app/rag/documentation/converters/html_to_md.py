"""
Convertit une page HTML en Markdown propre, en essayant d'exclure le bruit
courant des sites de documentation (menus de navigation, footers, barres
latérales) pour ne garder que le contenu utile à indexer dans le RAG.
"""
from bs4 import BeautifulSoup
from markdownify import markdownify as md


# Balises qu'on retire systématiquement avant conversion : elles ne
# contiennent jamais de contenu utile pour un RAG documentaire.
NOISE_TAGS = ["nav", "footer", "header", "script", "style", "aside"]


def convert(html_content: str, selector: str | None = None) -> str:
    """
    Convertit du HTML brut en Markdown.

    - selector : sélecteur CSS optionnel pour cibler la zone de contenu
      principale (ex: "main", "article", ".content"). Si absent, on tente
      "main" puis "article" avant de se rabattre sur tout le <body>.
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Supprime le bruit commun avant même de chercher la zone de contenu
    for tag_name in NOISE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    content_node = None
    if selector:
        content_node = soup.select_one(selector)

    if content_node is None:
        content_node = soup.find("main") or soup.find("article") or soup.body

    if content_node is None:
        # Cas limite : rien trouvé, on convertit tout par sécurité.
        content_node = soup

    markdown_text = md(str(content_node), heading_style="ATX")

    # Nettoyage final : trop de lignes vides consécutives rendent le
    # chunking moins efficace ensuite.
    lines = [line.rstrip() for line in markdown_text.splitlines()]
    cleaned_lines = []
    previous_blank = False
    for line in lines:
        is_blank = line.strip() == ""
        if is_blank and previous_blank:
            continue
        cleaned_lines.append(line)
        previous_blank = is_blank

    return "\n".join(cleaned_lines).strip()
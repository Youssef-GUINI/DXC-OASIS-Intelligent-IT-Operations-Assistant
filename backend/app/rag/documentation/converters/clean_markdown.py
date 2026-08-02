"""
Nettoie le bruit résiduel qui survit parfois à la conversion HTML→Markdown :
icônes, widgets d'export PDF, fils d'Ariane, liens communautaires/forum,
boutons de feedback... Règles génériques (pas propres à un seul site) pour
rester utile sur toutes les sources, Linux comme Storage.
"""
import re

# Lignes exactes à supprimer si elles apparaissent seules (boilerplate UI
# rencontré sur plusieurs sites de documentation). Comparaison faite après
# avoir retiré un éventuel marqueur de titre (#, ##...).
EXACT_JUNK_LINES = {
    "Cancel", "OK", "Creating your file...",
    "This may take a few minutes. Thanks for your patience.",
    "Your file is ready", "Suggest changes",
    "Send us an email", "Create a GitHub issue", "Feedback",
}

# Mots-clés qui, présents dans une ligne courte remplie de liens,
# trahissent un paragraphe "ressources communautaires" plutôt que du
# contenu technique réel.
COMMUNITY_LINK_KEYWORDS = [
    "Community Forum", "Discord", "Enterprise Support",
    "suggest content changes", "Feedback button", "GitHub issue",
]


def _is_icon_image_line(line: str) -> bool:
    """Une image sans texte alternatif et au format .svg est presque
    toujours une icône d'interface (flèche, loupe...), jamais du contenu."""
    return bool(re.fullmatch(r"!\[\]\([^)]*\.svg\)", line.strip()))


def _heading_content(line: str) -> str:
    """Retire un éventuel marqueur de titre Markdown (#, ##...) pour
    comparer le texte réel, peu importe son niveau de titre."""
    return re.sub(r"^#{1,6}\s*", "", line.strip())


def _link_anchor_texts(line: str) -> list[str]:
    return re.findall(r"\[([^\]]*)\]\([^)]*\)", line)


def _is_ui_action_link_line(line: str) -> bool:
    """Une ligne qui n'est composée que d'un ou deux liens dont le texte
    correspond à une action d'interface connue (pas du contenu)."""
    stripped = line.strip()
    anchors = _link_anchor_texts(stripped)
    if not anchors or len(anchors) > 2:
        return False

    # Texte total hors syntaxe de lien : doit être quasi vide pour que la
    # ligne soit "juste" un ou deux liens, rien d'autre.
    text_without_links = re.sub(r"\[[^\]]*\]\([^)]*\)", "", stripped)
    if len(re.sub(r"[^a-zA-Z]", "", text_without_links)) > 5:
        return False

    return any(anchor.strip() in EXACT_JUNK_LINES for anchor in anchors)


def _is_link_heavy_noise(line: str) -> bool:
    """Détecte une ligne saturée de liens et pauvre en vraies phrases —
    typique d'un fil d'Ariane ou d'un bloc de liens connexes."""
    stripped = line.strip()
    if not stripped:
        return False

    link_count = len(re.findall(r"\[[^\]]*\]\([^)]*\)", stripped))
    if link_count == 0:
        return False

    text_without_links = re.sub(r"\[[^\]]*\]\([^)]*\)", "", stripped)
    meaningful_chars = len(re.sub(r"[^a-zA-Z]", "", text_without_links))

    if link_count >= 2 and meaningful_chars < 15:
        return True

    if any(keyword.lower() in stripped.lower() for keyword in COMMUNITY_LINK_KEYWORDS):
        return True

    return False


def _strip_leading_breadcrumbs(lines: list[str]) -> list[str]:
    """Supprime les puces de navigation en tout début de document
    (ex: '* [All docs](...)'), avant que le vrai contenu ne commence."""
    result = list(lines)
    while result:
        stripped = result[0].strip()
        if stripped == "" or re.fullmatch(r"\* \[[^\]]*\]\([^)]*\)", stripped):
            result.pop(0)
            continue
        break
    return result


def clean(markdown_text: str) -> str:
    lines = markdown_text.splitlines()

    filtered = []
    for line in lines:
        stripped = line.strip()

        # Une icône SVG parfois collée directement à du texte (sans espace
        # ni saut de ligne) dans le HTML source : on la détache d'abord.
        stripped = re.sub(r"^!\[\]\([^)]*\.svg\)\s*", "", stripped)

        if stripped == "" and line.strip() != "":
            # La ligne ne contenait qu'une icône -> supprimée entièrement.
            continue
        if _is_icon_image_line(stripped):
            continue
        if _heading_content(stripped) in EXACT_JUNK_LINES:
            continue
        if _is_ui_action_link_line(stripped):
            continue
        if _is_link_heavy_noise(stripped):
            continue

        filtered.append(line if stripped == line.strip() else stripped)

    filtered = _strip_leading_breadcrumbs(filtered)

    # Recompresse les lignes vides multiples laissées par les suppressions
    final_lines = []
    previous_blank = False
    for line in filtered:
        is_blank = line.strip() == ""
        if is_blank and previous_blank:
            continue
        final_lines.append(line)
        previous_blank = is_blank

    return "\n".join(final_lines).strip()

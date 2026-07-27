"""
Orchestre le pipeline de documentation : lit config.yaml, télécharge
chaque source listée, la convertit en Markdown, et l'écrit dans le
dossier de connaissances du persona concerné (ex: rag/storage_kb/).

Usage :
    python updater.py                  # traite toutes les sources
    python updater.py --persona storage  # traite uniquement "storage"

Note : pas de "vrai" crawler ici (pas de découverte automatique de pages).
La liste des URLs est fixe, dans config.yaml — décision assumée pour
rester réaliste sur le temps disponible (voir discussion d'architecture).
"""
import argparse
from pathlib import Path

import requests
import yaml

from converters import html_to_md, pdf_to_md

# Dossier où vivent les bases de connaissances par persona, un cran
# au-dessus de documentation/ (donc rag/linux_kb/, rag/storage_kb/...).
RAG_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (OASIS-AI-Copilot documentation updater)"
}


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch(url: str) -> bytes:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.content


def process_source(persona: str, source: dict) -> None:
    url = source["url"]
    output_name = source["output"]
    fmt = source.get("format", "html")

    print(f"  → {url}")
    raw_content = fetch(url)

    if fmt == "html":
        markdown_text = html_to_md.convert(
            raw_content.decode("utf-8", errors="ignore"),
            selector=source.get("selector"),
        )
    elif fmt == "pdf":
        markdown_text = pdf_to_md.convert(raw_content, title=source.get("title"))
    else:
        raise ValueError(f"Format non supporté : {fmt}")

    output_dir = RAG_ROOT / f"{persona}_kb"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / output_name
    output_path.write_text(markdown_text, encoding="utf-8")
    print(f"    ✅ écrit : {output_path}")


def run(persona_filter: str | None = None) -> None:
    config = load_config()

    for persona, sources in config.items():
        if persona_filter and persona != persona_filter:
            continue
        if not sources:
            continue

        print(f"\nPersona: {persona}")
        for source in sources:
            try:
                process_source(persona, source)
            except Exception as exc:
                print(f"    ❌ échec pour {source['url']} : {exc}")

    print("\nTerminé. Pense à relancer l'indexation (index_directory) "
          "pour que les changements soient pris en compte dans ChromaDB.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Met à jour la documentation indexée dans le RAG.")
    parser.add_argument("--persona", help="Ne traiter qu'un persona précis (ex: storage)", default=None)
    args = parser.parse_args()

    run(persona_filter=args.persona)
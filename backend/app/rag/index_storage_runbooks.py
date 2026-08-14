import os
import frontmatter
from pathlib import Path
from groq import Groq
import chromadb

# Import de la configuration OASIS
try:
    from app.core.config import settings
    groq_api_key = getattr(settings, "groq_api_key", None) or os.environ.get("groq_api_key")
except Exception:
    groq_api_key = os.environ.get("groq_api_key")

if not groq_api_key:
    raise ValueError("La variable groq_api_key est introuvable dans la configuration OASIS ou l'environnement.")

# Initialisation globale du client Groq
client = Groq(api_key=groq_api_key)

# ==========================================
# CONFIGURATION EXCLUSIVE STORAGE
# ==========================================
BASE_RAG_DIR = Path(__file__).resolve().parent
STORAGE_KB_DIR = BASE_RAG_DIR / "storage_kb"
OUTPUT_RUNBOOKS_DIR = BASE_RAG_DIR / "storage_runbooks"
CHROMA_DB_DIR = BASE_RAG_DIR / "chroma_db"

OUTPUT_RUNBOOKS_DIR.mkdir(parents=True, exist_ok=True)

PROMPT_CONVERT_STORAGE_RUNBOOK = """
Tu es un expert Storage & Infrastructure SRE (NetApp, TrueNAS, AWS EBS/S3, Veeam) dans le système OASIS.
Ton rôle est de transformer le document de stockage brut ci-dessous en un RUNBOOK OPÉRATIONNEL au format Markdown structuré.

Tu dois impérativement inclure au début du fichier un header YAML (Frontmatter) avec cette structure :
---
id: id_unique_storage (ex: rb-netapp_volume_management, rb-aws_ebs_s3)
title: Titre clair de l'opération Storage
keywords:
  - mot_cle_1
  - mot_cle_2
mcp_read_tools:
  - outil_lecture_mcp (ex: get_capacity, list_snapshots, get_dr_status, list_backups)
mcp_action_tools:
  - outil_action_mcp (ex: resize_volume, create_snapshot, run_backup, restore_from_backup, initiate_failover)
risk_level: "LOW" ou "HIGH"
---

Règles strictes :
1. mcp_read_tools et mcp_action_tools ne doivent contenir QUE les outils directement pertinents au sujet.
2. risk_level = HIGH pour toute création, modification, restauration, failover ou suppression de volume/snapshot/backup.

Structure du corps Markdown :
# [Titre]

## 1. Symptômes & Déclencheurs Storage
## 2. Procédure de Diagnostic (Inquiry)
## 3. Arbre de Décision & Actions de Remédiation

Document brut :
----------------
{raw_content}
----------------

Renvoie UNIQUEMENT le contenu Markdown du Runbook (commençant par --- pour le YAML), sans aucun texte avant ou après.
"""

def convert_storage_kb_to_runbooks():
    """Convertit les documents du dossier storage_kb en Runbooks structurés."""
    if not STORAGE_KB_DIR.exists():
        print(f"[ATTENTION] Le dossier source {STORAGE_KB_DIR} n'existe pas.")
        return

    md_files = list(STORAGE_KB_DIR.glob("*.md"))

    if not md_files:
        print(f"[ATTENTION] Aucun fichier .md trouvé dans {STORAGE_KB_DIR}")
        return

    print(f"[STORAGE] Début de la conversion de {len(md_files)} document(s)...")

    for file_path in md_files:
        filename = file_path.name
        print(f"  -> Traitement Storage : {filename}...")

        raw_content = file_path.read_text(encoding="utf-8")

        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "user", "content": PROMPT_CONVERT_STORAGE_RUNBOOK.format(raw_content=raw_content)}
                ],
                temperature=0.1
            )

            formatted_runbook = response.choices[0].message.content

            output_path = OUTPUT_RUNBOOKS_DIR / f"rb_{filename}"
            output_path.write_text(formatted_runbook, encoding="utf-8")

            print(f"  [OK] Runbook Storage sauvegardé : {output_path}")

        except Exception as e:
            print(f"  [ERREUR] Conversion {filename} : {e}")

def index_storage_runbooks_to_chromadb():
    """Indexe les runbooks dans la collection ChromaDB 'oasis_storage_runbooks'."""
    runbook_files = list(OUTPUT_RUNBOOKS_DIR.glob("*.md"))

    if not runbook_files:
        print("[ATTENTION] Aucun runbook Storage formaté à indexer.")
        return

    print(f"\n[STORAGE] Indexation dans ChromaDB ({len(runbook_files)} fichiers)...")

    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = chroma_client.get_or_create_collection(name="oasis_storage_runbooks")

    for file_path in runbook_files:
        try:
            post = frontmatter.load(str(file_path))

            doc_id = str(post.metadata.get("id", file_path.name))
            content = post.content

            metadata = {
                "title": str(post.metadata.get("title", "")),
                "risk_level": str(post.metadata.get("risk_level", "LOW")),
                "mcp_read_tools": ",".join(post.metadata.get("mcp_read_tools", [])) if isinstance(post.metadata.get("mcp_read_tools"), list) else str(post.metadata.get("mcp_read_tools", "")),
                "mcp_action_tools": ",".join(post.metadata.get("mcp_action_tools", [])) if isinstance(post.metadata.get("mcp_action_tools"), list) else str(post.metadata.get("mcp_action_tools", "")),
                "keywords": ",".join(post.metadata.get("keywords", [])) if isinstance(post.metadata.get("keywords"), list) else str(post.metadata.get("keywords", ""))
            }

            collection.upsert(
                documents=[content],
                metadatas=[metadata],
                ids=[doc_id]
            )
            print(f"  [OK] Indexed ID : {doc_id} | Title : {metadata['title']}")

        except Exception as e:
            print(f"  [ERREUR] Indexation {file_path.name} : {e}")

    print("Indexation Storage terminée avec succès !")

if __name__ == "__main__":
    print("=== OASIS AGENT : ÉTAPE 1 - RUNBOOKS STORAGE DÉDIÉS ===")
    convert_storage_kb_to_runbooks()
    index_storage_runbooks_to_chromadb()
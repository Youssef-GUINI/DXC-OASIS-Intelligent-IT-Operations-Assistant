"""
Ajoute la colonne recurrence_count a la table incidents (idempotent : ne
plante pas si la colonne existe deja). N'efface ni ne modifie aucune donnee
existante ; les incidents deja en base recoivent la valeur par defaut 1.

Usage (depuis backend/, venv active) :
    python -m scripts.add_recurrence_column
"""
from sqlalchemy import text

from app.database.session import engine


def main():
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE incidents "
            "ADD COLUMN IF NOT EXISTS recurrence_count INTEGER NOT NULL DEFAULT 1"
        ))
    print("Colonne 'recurrence_count' presente sur la table incidents (ajoutee si besoin).")


if __name__ == "__main__":
    main()
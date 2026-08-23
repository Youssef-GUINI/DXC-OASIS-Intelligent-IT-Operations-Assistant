"""
Marque comme "resolved" les incidents de test tres anciens et jamais fermes
(typiquement les tout premiers incidents generes lors des premiers essais du
detecteur automatique, restes ouverts indefiniment).

Usage (depuis backend/, venv active) :
    python -m scripts.resolve_stale_incidents                   # dry-run
    python -m scripts.resolve_stale_incidents --confirm          # applique
    python -m scripts.resolve_stale_incidents --ids 1 2 3 --confirm
        # cible des IDs precis au lieu du critere par defaut
    python -m scripts.resolve_stale_incidents --older-than-days 5 --confirm
        # cible tout incident ouvert depuis plus de N jours (par defaut 5)
"""
import argparse
from datetime import datetime, timedelta, timezone

from app.database.session import SessionLocal
from app.models.incident import Incident


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm", action="store_true", help="Applique reellement. Sans ce flag : dry-run.")
    parser.add_argument("--ids", type=int, nargs="*", default=None, help="IDs precis a resoudre.")
    parser.add_argument(
        "--older-than-days", type=int, default=5,
        help="Ignore si --ids est fourni. Cible les incidents 'open' crees il y a plus de N jours (defaut: 5).",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.ids:
            query = db.query(Incident).filter(Incident.id.in_(args.ids), Incident.status == "open")
        else:
            cutoff = datetime.now(timezone.utc) - timedelta(days=args.older_than_days)
            query = db.query(Incident).filter(Incident.status == "open", Incident.created_at < cutoff)

        targets = query.order_by(Incident.id).all()

        if not targets:
            print("Rien a resoudre : aucun incident ne matche le critere.")
            return

        print(f"{len(targets)} incident(s) 'open' ancien(s) trouve(s) :\n")
        for incident in targets:
            preview = (incident.response or incident.user_message or "").replace("\n", " ")[:60]
            print(f"  #{incident.id:>4}  {incident.created_at}  cat={incident.category or 'N/A':<10}  {preview}")

        if not args.confirm:
            print(f"\n[DRY-RUN] Aucune modification effectuee. Relance avec --confirm pour marquer ces {len(targets)} incident(s) comme resolus.")
            return

        now = datetime.now(timezone.utc)
        for incident in targets:
            incident.status = "resolved"
            incident.resolved_at = now
        db.commit()
        print(f"\n{len(targets)} incident(s) marque(s) comme resolus avec succes.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
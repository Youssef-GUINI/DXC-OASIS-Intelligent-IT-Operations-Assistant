"""
Nettoie les incidents "pollues" crees par l'ancien save_incident() (avant le fix
qui empeche le chat de creer des incidents automatiquement).

Critere correct : source == "user" (uniquement le chat cree ces incidents ;
les incidents systeme, meme anciens et sans categorie, ont toujours source="system").

Usage (depuis backend/, venv active) :
    python -m scripts.cleanup_incidents                  # dry-run
    python -m scripts.cleanup_incidents --confirm         # supprime pour de vrai
    python -m scripts.cleanup_incidents --exclude 137 --confirm
        # exclut un ou plusieurs IDs precis de la suppression (ex: un incident
        # que tu veux garder malgre tout)
"""
import argparse

from app.database.session import SessionLocal
from app.models.incident import Incident
from app.models.report import Report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Supprime reellement les incidents. Sans ce flag : dry-run.",
    )
    parser.add_argument(
        "--exclude",
        type=int,
        nargs="*",
        default=[],
        help="IDs d'incidents a NE PAS supprimer, meme s'ils matchent le critere.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        query = db.query(Incident).filter(Incident.source == "user")

        if args.exclude:
            query = query.filter(~Incident.id.in_(args.exclude))

        targets = query.order_by(Incident.id).all()

        if not targets:
            print("Rien a nettoyer : aucun incident source='user' trouve.")
            return

        ids = [i.id for i in targets]

        print(f"{len(targets)} incident(s) 'pollue(s)' trouve(s) (source='user') :\n")
        for incident in targets:
            preview = (incident.user_message or "").replace("\n", " ")[:70]
            print(f"  #{incident.id:>4}  {incident.created_at}  {preview}")

        linked_reports = db.query(Report).filter(Report.incident_id.in_(ids)).all()
        if linked_reports:
            print(
                f"\n{len(linked_reports)} rapport(s) PDF pointent vers ces incidents "
                f"(ids: {[r.id for r in linked_reports]}). Ils seront detaches "
                f"(incident_id -> NULL), pas supprimes : le fichier PDF reste accessible."
            )

        if not args.exclude:
            print(
                "\nRappel : aucun ID exclu. Si tu veux garder un incident precis "
                "(ex: un exemple de qualite), relance avec --exclude <id>."
            )

        if not args.confirm:
            print(f"\n[DRY-RUN] Aucune suppression effectuee. Relance avec --confirm pour supprimer ces {len(targets)} incident(s).")
            return

        if linked_reports:
            db.query(Report).filter(Report.incident_id.in_(ids)).update(
                {Report.incident_id: None}, synchronize_session=False
            )

        db.query(Incident).filter(Incident.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
        print(f"\n{len(targets)} incident(s) supprime(s) avec succes.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
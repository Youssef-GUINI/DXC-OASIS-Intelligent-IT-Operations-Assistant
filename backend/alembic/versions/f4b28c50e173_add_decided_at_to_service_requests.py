"""add decided_at to service_requests

Le detail d'une demande n'affiche plus le fil de discussion ni l'historique :
il annonce le statut courant et la date de la decision. updated_at ne peut pas
jouer ce role -- il bouge a chaque modification ulterieure -- d'ou une colonne
dediee, retro-remplie depuis request_events pour les demandes deja tranchees.

Revision ID: f4b28c50e173
Revises: d9a3f17c6b42
Create Date: 2026-08-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f4b28c50e173'
down_revision = 'd9a3f17c6b42'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'service_requests',
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Retro-remplissage : premiere entree du journal amenant la demande a
    # APPROVED ou REJECTED. On prend la plus ancienne, celle de la decision
    # elle-meme, et non une reouverture eventuelle.
    op.execute(
        """
        UPDATE service_requests AS r
        SET decided_at = decision.created_at
        FROM (
            SELECT request_id, MIN(created_at) AS created_at
            FROM request_events
            WHERE to_status IN ('APPROVED', 'REJECTED')
            GROUP BY request_id
        ) AS decision
        WHERE decision.request_id = r.id
        """
    )


def downgrade() -> None:
    op.drop_column('service_requests', 'decided_at')

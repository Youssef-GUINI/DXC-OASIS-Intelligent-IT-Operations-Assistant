"""Relie le chat d'investigation aux incidents et aux actions proposées

Le cycle de vie d'un incident -- détection, diagnostic, proposition d'action,
confirmation humaine, résolution -- se déroulait jusqu'ici dans trois endroits
sans lien entre eux : le ticket, le fil de chat et l'ActionRequest. Rien ne
permettait de rouvrir l'investigation d'un ticket, ni de savoir quel message
avait proposé quelle action.

Deux rattachements suffisent :
  - chat_conversations.incident_ticket_id : le fil d'investigation du ticket,
    rouvert tel quel au lieu d'en ouvrir un second ;
  - action_requests.chat_message_id : le message qui porte la proposition.
    Le lien est posé de ce côté-ci, et non l'inverse : un même tour peut
    proposer plusieurs actions, et c'est ce qui permet de réafficher leurs
    boutons Confirmer/Rejeter au rechargement du fil, pas seulement dans la
    réponse immédiate du tour.

Revision ID: b6d0f3a91c47
Revises: a1c7e94d2f80
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = 'b6d0f3a91c47'
down_revision = 'a1c7e94d2f80'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat_conversations",
        sa.Column("incident_ticket_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_chat_conversations_incident_ticket",
        "chat_conversations",
        "incident_tickets",
        ["incident_ticket_id"],
        ["id"],
        ondelete="SET NULL",
    )
    # Un ingénieur n'a qu'un fil d'investigation par ticket : l'unicité est ce
    # qui permet de rouvrir l'existant sans arbitrer entre plusieurs candidats.
    # La clé porte aussi user_id, une conversation appartenant à une personne
    # et n'étant lisible que par elle -- deux ingénieurs sur le même incident
    # ont donc chacun le sien. L'index est partiel, la colonne étant nulle
    # pour les fils ordinaires, qui sont la majorité.
    op.create_index(
        "uq_chat_conversations_incident_ticket",
        "chat_conversations",
        ["incident_ticket_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("incident_ticket_id IS NOT NULL"),
    )

    op.add_column(
        "action_requests",
        sa.Column("chat_message_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_action_requests_chat_message",
        "action_requests",
        "chat_messages",
        ["chat_message_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_action_requests_chat_message_id", "action_requests", ["chat_message_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_action_requests_chat_message_id", table_name="action_requests")
    op.drop_constraint("fk_action_requests_chat_message", "action_requests", type_="foreignkey")
    op.drop_column("action_requests", "chat_message_id")

    op.drop_index("uq_chat_conversations_incident_ticket", table_name="chat_conversations")
    op.drop_constraint(
        "fk_chat_conversations_incident_ticket", "chat_conversations", type_="foreignkey"
    )
    op.drop_column("chat_conversations", "incident_ticket_id")

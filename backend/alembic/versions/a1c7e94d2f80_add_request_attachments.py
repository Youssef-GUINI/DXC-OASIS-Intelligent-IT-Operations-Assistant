"""add request_attachments

Fichiers joints a une demande (rapport demande, capture, export). Le binaire
vit sur disque comme pour le Data Hub ; cette table n'en garde que les
metadonnees et le lien vers la demande.

Revision ID: a1c7e94d2f80
Revises: f4b28c50e173
Create Date: 2026-08-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1c7e94d2f80'
down_revision = 'f4b28c50e173'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'request_attachments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('request_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('uploaded_by', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('stored_path', sa.String(), nullable=False),
        sa.Column('content_type', sa.String(length=120), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column(
            'created_at', sa.DateTime(timezone=True),
            server_default=sa.text('now()'), nullable=False,
        ),
        sa.ForeignKeyConstraint(['request_id'], ['service_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_request_attachments_request_id'),
        'request_attachments', ['request_id'],
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_request_attachments_request_id'), table_name='request_attachments')
    op.drop_table('request_attachments')

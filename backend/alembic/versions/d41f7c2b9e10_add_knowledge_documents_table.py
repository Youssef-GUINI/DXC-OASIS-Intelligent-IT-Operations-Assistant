"""add knowledge_documents table (Data Hub)

Revision ID: d41f7c2b9e10
Revises: c93419b63533
Create Date: 2026-08-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd41f7c2b9e10'
down_revision = 'c93419b63533'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'knowledge_documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('stored_path', sa.String(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('collection', sa.String(), nullable=False),
        sa.Column('chunk_count', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'INDEXED', 'FAILED', name='documentstatus'), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('uploaded_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('indexed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_knowledge_documents_collection'),
        'knowledge_documents',
        ['collection'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_knowledge_documents_collection'), table_name='knowledge_documents')
    op.drop_table('knowledge_documents')
    sa.Enum(name='documentstatus').drop(op.get_bind(), checkfirst=True)

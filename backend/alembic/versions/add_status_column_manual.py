"""add missing status column to incidents

Revision ID: a1f2b3c4d5e6
Revises: e8c39c160f78
Create Date: 2026-08-10 01:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1f2b3c4d5e6'
down_revision = 'e8c39c160f78'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('incidents', sa.Column('status', sa.String(length=20), nullable=False, server_default='open'))


def downgrade() -> None:
    op.drop_column('incidents', 'status')
"""add disk_metrics table (real performance history)

Revision ID: f7c1b0d5a983
Revises: e58a3d9c4712
Create Date: 2026-08-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f7c1b0d5a983'
down_revision = 'e58a3d9c4712'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'disk_metrics',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('device', sa.String(), nullable=False),
        sa.Column('iops', sa.Float(), nullable=False),
        sa.Column('throughput_mbps', sa.Float(), nullable=False),
        sa.Column('latency_ms', sa.Float(), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_disk_metrics_device'), 'disk_metrics', ['device'], unique=False)
    op.create_index(op.f('ix_disk_metrics_recorded_at'), 'disk_metrics', ['recorded_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_disk_metrics_recorded_at'), table_name='disk_metrics')
    op.drop_index(op.f('ix_disk_metrics_device'), table_name='disk_metrics')
    op.drop_table('disk_metrics')

"""add mcp_calls table

Le modèle app/models/mcp_call.py existait déjà et StorageMCPClient.call_tool()
l'utilise, mais aucune migration ne créait la table : tout appel à
log_mcp_call() aurait échoué. Cette révision comble le manque.

Revision ID: e58a3d9c4712
Revises: d41f7c2b9e10
Create Date: 2026-08-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e58a3d9c4712'
down_revision = 'd41f7c2b9e10'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'mcp_calls',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('persona', sa.String(), nullable=False),
        sa.Column('tool_name', sa.String(), nullable=False),
        sa.Column('arguments', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.Enum('SUCCESS', 'FAILED', 'DENIED', name='mcpcallstatus'), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('action_request_id', sa.UUID(), nullable=True),
        sa.Column('correlation_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['action_request_id'], ['action_requests.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_mcp_calls_user_id'), 'mcp_calls', ['user_id'], unique=False)
    op.create_index(op.f('ix_mcp_calls_persona'), 'mcp_calls', ['persona'], unique=False)
    op.create_index(op.f('ix_mcp_calls_tool_name'), 'mcp_calls', ['tool_name'], unique=False)
    op.create_index(op.f('ix_mcp_calls_action_request_id'), 'mcp_calls', ['action_request_id'], unique=False)
    op.create_index(op.f('ix_mcp_calls_correlation_id'), 'mcp_calls', ['correlation_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_mcp_calls_correlation_id'), table_name='mcp_calls')
    op.drop_index(op.f('ix_mcp_calls_action_request_id'), table_name='mcp_calls')
    op.drop_index(op.f('ix_mcp_calls_tool_name'), table_name='mcp_calls')
    op.drop_index(op.f('ix_mcp_calls_persona'), table_name='mcp_calls')
    op.drop_index(op.f('ix_mcp_calls_user_id'), table_name='mcp_calls')
    op.drop_table('mcp_calls')
    sa.Enum(name='mcpcallstatus').drop(op.get_bind(), checkfirst=True)

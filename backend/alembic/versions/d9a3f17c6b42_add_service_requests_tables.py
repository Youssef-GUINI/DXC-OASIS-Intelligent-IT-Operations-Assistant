"""add service_requests, request_messages, request_events

Canal de demandes entre un ingenieur et l'administrateur, dans les deux sens
(voir app/models/service_request.py). Trois tables : la demande, son fil de
discussion, et le journal de ses changements de statut.

Revision ID: d9a3f17c6b42
Revises: c7e1a94b3d20
Create Date: 2026-08-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd9a3f17c6b42'
down_revision = 'c7e1a94b3d20'
branch_labels = None
depends_on = None


# create_type=False : sans ce drapeau, op.create_table reemet un CREATE TYPE
# pour chaque colonne enum, apres la creation explicite ci-dessous -- et la
# migration echoue sur "type already exists" dans sa propre transaction.
direction_enum = postgresql.ENUM(
    'ENGINEER_TO_ADMIN', 'ADMIN_TO_ENGINEER',
    name='requestdirection', create_type=False,
)
priority_enum = postgresql.ENUM(
    'LOW', 'MEDIUM', 'HIGH', 'CRITICAL',
    name='requestpriority', create_type=False,
)
status_enum = postgresql.ENUM(
    'PENDING', 'COMPLETED', 'IN_REVIEW', 'APPROVED', 'REJECTED',
    'ACKNOWLEDGED', 'IN_PROGRESS',
    name='requeststatus', create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    direction_enum.create(bind, checkfirst=True)
    priority_enum.create(bind, checkfirst=True)
    status_enum.create(bind, checkfirst=True)

    op.create_table(
        'service_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('direction', direction_enum, nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('request_type', sa.String(length=60), nullable=True),
        sa.Column('priority', priority_enum, nullable=False),
        sa.Column('status', status_enum, nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('assigned_to', sa.Integer(), nullable=False),
        sa.Column('deadline', sa.DateTime(timezone=True), nullable=True),
        sa.Column('administrator_response', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_service_requests_direction'), 'service_requests', ['direction'])
    op.create_index(op.f('ix_service_requests_status'), 'service_requests', ['status'])
    op.create_index(op.f('ix_service_requests_created_by'), 'service_requests', ['created_by'])
    op.create_index(op.f('ix_service_requests_assigned_to'), 'service_requests', ['assigned_to'])

    op.create_table(
        'request_messages',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('request_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['request_id'], ['service_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_request_messages_request_id'), 'request_messages', ['request_id'])

    op.create_table(
        'request_events',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('request_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('actor_id', sa.Integer(), nullable=False),
        sa.Column('from_status', status_enum, nullable=True),
        sa.Column('to_status', status_enum, nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['request_id'], ['service_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_request_events_request_id'), 'request_events', ['request_id'])


def downgrade() -> None:
    op.drop_table('request_events')
    op.drop_table('request_messages')
    op.drop_table('service_requests')
    bind = op.get_bind()
    status_enum.drop(bind, checkfirst=True)
    priority_enum.drop(bind, checkfirst=True)
    direction_enum.drop(bind, checkfirst=True)

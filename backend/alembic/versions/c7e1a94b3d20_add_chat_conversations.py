"""add chat_conversations (plusieurs fils par utilisateur)

Les messages étaient rattachés directement à un utilisateur : un seul fil,
effacé d'un bloc. Ils appartiennent désormais à une conversation, et
l'utilisateur possède la conversation.

Les messages existants ne sont pas perdus : chaque utilisateur qui en avait
reçoit une conversation reprenant tout son historique.

Revision ID: c7e1a94b3d20
Revises: b2f4d6c81a05
Create Date: 2026-08-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c7e1a94b3d20'
down_revision = 'b2f4d6c81a05'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'chat_conversations',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=120), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_chat_conversations_user_id'), 'chat_conversations', ['user_id'], unique=False)

    op.add_column('chat_messages', sa.Column('conversation_id', sa.BigInteger(), nullable=True))

    # Reprise de l'existant : une conversation par utilisateur ayant déjà
    # discuté, datée de son premier et de son dernier message.
    op.execute(
        """
        INSERT INTO chat_conversations (user_id, title, created_at, updated_at)
        SELECT user_id, 'Previous conversation', MIN(created_at), MAX(created_at)
        FROM chat_messages
        GROUP BY user_id
        """
    )
    op.execute(
        """
        UPDATE chat_messages AS m
        SET conversation_id = c.id
        FROM chat_conversations AS c
        WHERE c.user_id = m.user_id
        """
    )

    op.alter_column('chat_messages', 'conversation_id', nullable=False)
    op.create_foreign_key(
        'fk_chat_messages_conversation_id',
        'chat_messages',
        'chat_conversations',
        ['conversation_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_index(op.f('ix_chat_messages_conversation_id'), 'chat_messages', ['conversation_id'], unique=False)

    op.drop_index(op.f('ix_chat_messages_user_id'), table_name='chat_messages')
    op.drop_column('chat_messages', 'user_id')


def downgrade() -> None:
    op.add_column('chat_messages', sa.Column('user_id', sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE chat_messages AS m
        SET user_id = c.user_id
        FROM chat_conversations AS c
        WHERE c.id = m.conversation_id
        """
    )
    # Un message dont la conversation a disparu n'a plus de propriétaire : la
    # colonne redevenant obligatoire, il n'y a rien à en faire.
    op.execute("DELETE FROM chat_messages WHERE user_id IS NULL")
    op.alter_column('chat_messages', 'user_id', nullable=False)
    op.create_foreign_key('fk_chat_messages_user_id', 'chat_messages', 'users', ['user_id'], ['id'])
    op.create_index(op.f('ix_chat_messages_user_id'), 'chat_messages', ['user_id'], unique=False)

    op.drop_index(op.f('ix_chat_messages_conversation_id'), table_name='chat_messages')
    op.drop_constraint('fk_chat_messages_conversation_id', 'chat_messages', type_='foreignkey')
    op.drop_column('chat_messages', 'conversation_id')

    op.drop_index(op.f('ix_chat_conversations_user_id'), table_name='chat_conversations')
    op.drop_table('chat_conversations')

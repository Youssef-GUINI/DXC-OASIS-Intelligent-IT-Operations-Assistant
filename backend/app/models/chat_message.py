"""
app/models/chat_message.py

Conversations entre l'ingénieur et OASIS, et messages qui les composent.

Le chat était purement local au composant React : quitter la page suffisait à
perdre l'échange. Tout est désormais écrit ici, ce qui permet de rouvrir une
conversation, d'en mener plusieurs en parallèle (un incident d'un côté, une
question de capacité de l'autre) et de donner à l'agent le contexte des
messages précédents.

L'identifiant des messages est un entier auto-incrémenté, contrairement aux
autres tables métier : c'est lui qui donne l'ordre du fil. Les deux messages
d'un même tour sont écrits dans la même transaction et partagent donc le
created_at renvoyé par now() -- trier sur la date seule les rendrait
interchangeables, et la réponse pourrait s'afficher avant la question.

Le rôle est stocké en texte : deux valeurs suffisent, un type énuméré
PostgreSQL de plus n'apporterait rien.
"""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database.base import Base

ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"

TITLE_MAX_LENGTH = 120


class ChatConversation(Base):
    """Un fil de discussion. Appartient à un utilisateur et à lui seul."""

    __tablename__ = "chat_conversations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Repris du premier message, puis renommable. Jamais vide : une entrée sans
    # libellé dans la liste latérale serait impossible à retrouver.
    title = Column(String(TITLE_MAX_LENGTH), nullable=False)

    # Fil d'investigation d'un incident : renseigné quand la conversation a
    # été ouverte depuis un ticket. C'est ce qui distingue une investigation
    # d'une question ordinaire -- l'agent reçoit alors le contexte du ticket,
    # et le drawer rouvre le fil au lieu d'en créer un second.
    incident_ticket_id = Column(
        UUID(as_uuid=True),
        ForeignKey("incident_tickets.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Avancé à chaque tour enregistré : c'est l'ordre de la liste latérale, la
    # conversation en cours doit remonter en tête.
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User")
    incident_ticket = relationship("IncidentTicket")
    messages = relationship(
        "ChatMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatMessage.id",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Le propriétaire se lit sur la conversation : le dupliquer ici ouvrirait
    # la porte à un message rattaché à un fil qui n'est pas le sien.
    conversation_id = Column(
        BigInteger,
        ForeignKey("chat_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    conversation = relationship("ChatConversation", back_populates="messages")

    # Actions proposées par ce message et pas encore exécutées. Le lien est
    # porté par action_requests : un même tour peut en proposer plusieurs.
    action_requests = relationship(
        "ActionRequest",
        back_populates="chat_message",
        order_by="ActionRequest.created_at",
    )

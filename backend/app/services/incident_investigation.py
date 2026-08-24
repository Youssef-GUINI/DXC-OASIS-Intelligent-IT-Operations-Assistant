"""
app/services/incident_investigation.py

Deuxième étape du cycle de vie d'un incident : le diagnostic.

« Investigate with OASIS » ouvrait le chat vide, à charge pour l'ingénieur de
réexpliquer lui-même l'incident qu'il venait de lire à l'écran. Le bouton
ouvre désormais un fil rattaché au ticket, dans lequel l'agent a déjà lu les
journaux de la VM, énoncé une cause racine et proposé une remédiation à
confirmer.

Le fil reste un vrai chat : l'ingénieur y répond, conteste, demande autre
chose. C'est le point du cycle où la machine propose et où l'humain décide,
et un écran figé ne rendrait pas ce dialogue.

Le diagnostic est ensuite recopié sur le ticket (`root_cause`,
`impact_summary`) par une seconde passe de synthèse : la réponse de l'agent
est de la prose, la fiche d'incident a besoin de deux champs courts.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.llm.groq_client import groq_client
from app.mcp.storage.server import REMEDIATION_TOOLS
from app.models.chat_message import ChatConversation
from app.models.incident_ticket import IncidentTicket
from app.models.user import User
from app.personas.storage.agent import IncidentContext, storage_persona
from app.services import chat_service, incident_service

logger = logging.getLogger(__name__)

_SUMMARY_SYSTEM_PROMPT = (
    "You summarise a technical diagnosis that has already been established. You "
    "do not diagnose anything yourself and you add no information absent from "
    "the text you were given."
)

_SUMMARY_INSTRUCTIONS = """Here is the analysis the Storage agent produced for an incident.

--- ANALYSIS ---
{analysis}
--- END ---

Return ONLY a JSON object, with no surrounding text and no code fence:
{{"root_cause": "...", "impact_summary": "..."}}

  - root_cause: the root cause in one sentence, as it emerges from the
    analysis. If the analysis reaches no conclusion, write exactly
    "Root cause not established at this stage."
  - impact_summary: the concrete operational consequence, one sentence.

Both values are in English, whatever language the analysis is written in."""


def _investigation_prompt(ticket: IncidentTicket) -> str:
    """
    Le premier message du fil, écrit à la place de l'ingénieur.

    Il est enregistré tel quel comme message utilisateur : en relisant le fil
    six mois plus tard, on voit la question qui a lancé l'analyse, et non un
    diagnostic tombé de nulle part.
    """
    return (
        f"Diagnose incident {ticket.ticket_number}: \"{ticket.title}\" on "
        f"{ticket.affected_system}. Read the journals and the current state on "
        f"the VM, tell me the root cause, then propose the right remediation."
    )


def _parse_summary(raw: str) -> dict[str, str]:
    """
    Extrait le JSON de synthèse, même enveloppé dans un bloc de code.

    Le modèle reçoit la consigne de ne rien mettre autour, et l'y tient la
    plupart du temps -- mais un diagnostic perdu parce qu'il a ajouté ```json
    serait une régression invisible : on découpe donc entre la première
    accolade et la dernière.
    """
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        return {}
    try:
        parsed = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {
        key: str(value).strip()
        for key, value in parsed.items()
        if key in ("root_cause", "impact_summary") and value
    }


def _summarise(analysis: str) -> dict[str, str]:
    try:
        raw = groq_client.chat(
            _SUMMARY_INSTRUCTIONS.format(analysis=analysis),
            system_prompt=_SUMMARY_SYSTEM_PROMPT,
        )
    except Exception:  # noqa: BLE001 -- Groq indisponible
        logger.exception("Synthèse du diagnostic impossible")
        return {}
    return _parse_summary(raw or "")


def find_conversation(
    db: Session, *, ticket_id: uuid.UUID, user_id: int
) -> Optional[ChatConversation]:
    """
    Le fil d'investigation de ce ticket pour cet utilisateur, s'il existe.

    Le fil est par utilisateur et non par ticket : une conversation appartient
    à une personne et n'est lisible que par elle (cf. chat_service). Deux
    ingénieurs qui investiguent le même incident ont donc chacun le leur.
    """
    return db.execute(
        select(ChatConversation).where(
            ChatConversation.incident_ticket_id == ticket_id,
            ChatConversation.user_id == user_id,
        )
    ).scalars().first()


def _fallback_action(
    db: Session, ticket: IncidentTicket, user_id: int
) -> Optional[uuid.UUID]:
    """
    Propose la remédiation prévue par la règle de détection.

    Filet de sécurité, et non doublon du travail de l'agent : le modèle décrit
    volontiers la remédiation en recopiant un appel d'outil en JSON dans sa
    réponse au lieu de l'émettre. Écrit ainsi, l'appel ne crée rien, et
    l'ingénieur se retrouve devant un diagnostic sans bouton -- le cycle
    s'arrête à l'avant-dernière marche.

    Ce que la règle a calculé au moment de la détection suffit pourtant :
    `recommendations` porte déjà l'`action_type` et la cible technique. On ne
    demande donc au modèle que ce que lui seul sait faire, le diagnostic, et
    on tient la proposition de ce qui est déterministe.
    """
    already = {
        (action.action_type, action.target)
        for action in ticket.action_requests
        if action.status.value in ("pending", "confirmed", "completed")
    }

    for recommendation in ticket.recommendations or []:
        action_type = recommendation.get("action_type")
        if action_type not in REMEDIATION_TOOLS:
            continue

        target = recommendation.get("target") or context_for(ticket).technical_id
        if not target or (action_type, target) in already:
            continue

        action = incident_service.create_action_request(
            db,
            user_id=user_id,
            action_type=action_type,
            target=target,
            parameters={"target": target},
            incident_ticket_id=ticket.id,
        )
        return action.id

    return None


def context_for(ticket: IncidentTicket) -> IncidentContext:
    """Le ticket sous la forme que l'agent attend, pour tout tour du fil."""
    return IncidentContext(
        ticket_id=ticket.id,
        ticket_number=ticket.ticket_number,
        title=ticket.title,
        description=ticket.description,
        severity=ticket.severity.value,
        affected_system=ticket.affected_system,
        mcp_data=ticket.mcp_data or {},
    )


async def start(db: Session, *, ticket: IncidentTicket, user: User) -> dict[str, Any]:
    """
    Ouvre l'investigation d'un ticket et renvoie de quoi afficher le fil.

    Un fil déjà ouvert est repris tel quel, sans relancer l'agent : rouvrir le
    panneau d'un incident ne doit ni dupliquer les fils, ni reproposer une
    action que l'ingénieur vient de rejeter.
    """
    existing = find_conversation(db, ticket_id=ticket.id, user_id=user.id)
    if existing is not None:
        return {"conversation_id": existing.id, "created": False}

    context = context_for(ticket)
    question = _investigation_prompt(ticket)

    # L'agent tourne avant toute écriture : s'il échoue, l'exception remonte
    # et le ticket est inchangé, plutôt que de laisser un fil vide rattaché.
    turn = await storage_persona.handle_message(
        question, created_by=user.id, incident=context
    )

    conversation = chat_service.create_conversation(
        db, user.id, title=f"{ticket.ticket_number} — investigation"
    )
    conversation.incident_ticket_id = ticket.id
    db.commit()

    _, assistant_message = chat_service.save_turn(
        db, conversation, question=question, answer=turn.text
    )

    proposed = list(turn.proposed_action_ids)
    if not proposed:
        fallback = _fallback_action(db, ticket, user.id)
        if fallback is not None:
            proposed.append(fallback)

    chat_service.attach_actions(db, assistant_message, proposed)
    incident_service.mark_in_progress(db, ticket)

    summary = _summarise(turn.text)
    if summary:
        ticket.root_cause = summary.get("root_cause") or ticket.root_cause
        ticket.impact_summary = summary.get("impact_summary") or ticket.impact_summary
        db.commit()

    incident_service.add_note(
        db,
        ticket_id=ticket.id,
        author_id=user.id,
        content=(
            f"Investigation opened by {user.full_name or user.email}. "
            f"OASIS analysed the VM and "
            + (
                f"proposed {len(proposed)} action(s) for confirmation."
                if proposed
                else "found no action it can automate."
            )
        ),
    )
    db.refresh(ticket)

    return {"conversation_id": conversation.id, "created": True}

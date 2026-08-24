"""Persona Storage : RAG, tool calling Groq et garde-fou d'actions."""
from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.llm.groq_client import groq_client
from app.mcp.storage.client import StorageMCPClient
from app.mcp.storage.server import REMEDIATION_TOOLS
from app.personas.storage.incident_rules import evaluate_tool_result
from app.personas.storage.prompts import STORAGE_SYSTEM_PROMPT
from app.rag.retriever import retriever
from app.services import incident_service

# session.py confirme : SessionLocal est un sessionmaker SYNC classique
# (sqlalchemy.orm.sessionmaker), pas un async_sessionmaker.
from app.database.session import SessionLocal

logger = logging.getLogger(__name__)

_MAX_TOOL_ROUNDS = 6

# Arguments sous lesquels les outils de remediation nomment leur cible :
# run_backup(target=...), create_snapshot(volume_id=...),
# restore_from_backup(target=..., backup_id=...).
_TARGET_ARGUMENTS = ("target", "volume_id", "job_id")


@dataclass
class IncidentContext:
    """
    Le ticket sur lequel porte une investigation.

    Des champs figes plutot qu'un IncidentTicket ORM : l'agent ouvre ses
    propres sessions et vit plus longtemps que celle de la requete HTTP --
    une entite detachee y deviendrait inutilisable a la premiere lecture
    d'attribut.
    """

    ticket_id: uuid.UUID
    ticket_number: str
    title: str
    description: str
    severity: str
    affected_system: str
    mcp_data: dict[str, Any] = field(default_factory=dict)

    @property
    def technical_id(self) -> str | None:
        """
        L'identifiant a passer aux outils, par opposition au libelle affiche.

        `affected_system` est la Description systemd de l'unit -- « Sauvegarde
        de l'application critique » -- alors que les outils attendent
        `backup-app-critical.timer`. Confondre les deux fait echouer l'action
        au moment ou l'ingenieur la confirme, c'est-a-dire au pire moment.
        """
        for key in ("job_id", "volume_id", "mountpoint"):
            value = self.mcp_data.get(key)
            if value:
                return str(value)
        return None

    def as_prompt_block(self) -> str:
        reading = json.dumps(self.mcp_data, ensure_ascii=False, indent=2)
        target = self.technical_id or "(no technical identifier recorded)"
        return f"""
INVESTIGATION IN PROGRESS -- ticket {self.ticket_number} ({self.severity}).
  Title               : {self.title}
  Resource (label)    : {self.affected_system}
  Technical target    : {target}
  Initial finding     : {self.description}
  MCP reading taken at detection time:
{reading}

Run the diagnosis yourself, in this order:
  1. Read the evidence on the VM with the read-only tools. For a failed backup,
     get_backup_logs on the job is the most direct source; get_backup_job_status
     gives its current state.
  2. State the root cause in one sentence, grounded in what you read. Invent no
     log line: if the journal says nothing, say so.
  3. Propose ONE remediation by ACTUALLY CALLING the matching tool, with
     "{target}" as the target -- never the human-readable label.

On that last point there is no room for approximation: writing a tool call as
JSON in your answer creates no proposal, and the engineer will have no button
to click. Only a real tool call records the remediation. Calling it does not
execute it: it puts it in the queue awaiting their confirmation.

When the cause first requires a manual fix on the VM -- recreating a missing
backup repository, for instance -- still propose the action that comes next,
typically re-running the job, and say in your answer what the administrator
must do before confirming it. The proposal waits for their click: it will not
run before the prerequisite is met, and that is exactly what the confirmation
step is for.

Only refrain from calling a tool if none of them relates to the incident.
"""


# Un objet JSON, avec au plus un niveau d'imbrication -- de quoi attraper
# {"tool": "...", "args": {...}} sans écrire un analyseur complet.
_JSON_OBJECT = re.compile(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", re.DOTALL)


def _candidate_calls(parsed: dict) -> list[tuple[str, dict]]:
    """
    Les formes sous lesquelles un modele ecrit un appel d'outil en prose.

    Elles varient d'un modele a l'autre et d'un tour a l'autre : {"tool": …,
    "args": {…}}, {"name": …, "arguments": {…}}, ou simplement le nom de
    l'outil en cle. On les accepte toutes, la validation venant ensuite.
    """
    calls: list[tuple[str, dict]] = []

    for name_key, args_key in (("tool", "args"), ("name", "arguments"), ("tool", "parameters")):
        name = parsed.get(name_key)
        if isinstance(name, str):
            arguments = parsed.get(args_key)
            calls.append((name, arguments if isinstance(arguments, dict) else parsed))

    for key, value in parsed.items():
        if isinstance(value, dict) and key in REMEDIATION_TOOLS:
            calls.append((key, value))

    return calls


def _recover_written_call(text: str, incident: "IncidentContext") -> tuple[str, dict] | None:
    """
    Recupere un appel d'outil que le modele a ecrit au lieu de l'emettre.

    C'est le defaut le plus couteux de la boucle : le diagnostic est juste, la
    remediation est la bonne, mais elle est recopiee en JSON dans la reponse.
    Ecrite ainsi elle ne cree rien, et l'ingenieur lit une analyse complete
    sans avoir aucun bouton a cliquer -- le cycle s'arrete a l'avant-derniere
    marche alors que tout le travail est fait.

    La recuperation n'ouvre aucune latitude au modele : l'outil doit etre un
    outil de remediation connu, et la cible doit designer la ressource du
    ticket en cours. Une cible inventee, ou portant sur une autre machine, est
    ignoree. Et ce qui en sort reste une proposition en attente, soumise au
    meme clic humain que le reste.
    """
    allowed = {incident.affected_system}
    if incident.technical_id:
        allowed.add(incident.technical_id)

    for blob in _JSON_OBJECT.findall(text):
        try:
            parsed = json.loads(blob)
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, dict):
            continue

        for tool_name, arguments in _candidate_calls(parsed):
            if tool_name not in REMEDIATION_TOOLS:
                continue
            target = next(
                (str(arguments[key]) for key in _TARGET_ARGUMENTS if arguments.get(key)),
                None,
            )
            if target in allowed:
                return tool_name, arguments

    return None


@dataclass
class AgentTurn:
    """
    Ce qu'un tour a produit : le texte, et les actions mises en attente.

    handle_message renvoyait une simple chaine. Les propositions d'action
    doivent remonter jusqu'a la route pour etre rattachees au message qui les
    porte -- sans quoi l'interface ne saurait pas quels boutons afficher.
    """

    text: str
    proposed_action_ids: list[uuid.UUID] = field(default_factory=list)


class StoragePersona:
    name = "storage_persona"
    rag_collection = "storage_kb"

    def _propose_action(
        self,
        db,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        created_by: int,
        incident: IncidentContext | None,
    ) -> tuple[dict[str, Any], uuid.UUID | None]:
        """
        Transforme un appel d'outil de remediation en proposition en attente.

        C'est le garde-fou central : le modele croit declencher l'action, il
        n'en enregistre que l'intention. Le seul chemin d'execution reste
        POST /storage/actions/{id}/confirm, derriere un clic humain.
        """
        target = next(
            (str(arguments[key]) for key in _TARGET_ARGUMENTS if arguments.get(key)),
            None,
        )
        if target is None:
            return {
                "status": "error",
                "message": f"{tool_name} requires an explicit target "
                           f"({' or '.join(_TARGET_ARGUMENTS)}).",
            }, None

        # Le modele confond volontiers le libelle affiche du ticket avec
        # l'identifiant de l'unit systemd, les deux etant sous ses yeux. Une
        # action enregistree sur le libelle echouerait a l'execution, apres
        # que l'ingenieur l'a confirmee : on retablit l'identifiant technique
        # du ticket, qui designe la meme chose sans ambiguite.
        if incident is not None and target == incident.affected_system:
            corrected = incident.technical_id
            if corrected:
                logger.info(
                    "Cible de %s corrigee : %r -> %r", tool_name, target, corrected
                )
                target = corrected
                arguments = {**arguments, **{
                    key: corrected for key in _TARGET_ARGUMENTS if key in arguments
                }}

        # `confirm` est ajoute par confirm_and_execute_action au moment de
        # l'execution : le laisser ici le passerait deux fois au meme appel.
        parameters = {key: value for key, value in arguments.items() if key != "confirm"}

        try:
            action = incident_service.create_action_request(
                db,
                user_id=created_by,
                action_type=tool_name,
                target=target,
                parameters=parameters,
                incident_ticket_id=incident.ticket_id if incident else None,
            )
        except Exception:  # noqa: BLE001
            logger.exception("Echec de l'enregistrement d'une proposition d'action")
            return {
                "status": "error",
                "message": "Proposal not recorded, try again.",
            }, None

        return {
            "status": "awaiting_confirmation",
            "action_type": tool_name,
            "target": target,
            "message": "Action NOT executed: it has been proposed to the engineer, "
                       "who confirms or rejects it from the interface. "
                       "Present it as a recommendation, never as a fact.",
        }, action.id

    async def handle_message(
        self,
        user_message: str,
        created_by: int | None = None,
        history: list[dict[str, str]] | None = None,
        incident: IncidentContext | None = None,
    ) -> AgentTurn:
        """
        Repond a un message, en tenant compte des tours precedents.

        `history` contient les derniers messages du fil (role user/assistant),
        deja tronque par chat_service : sans lui, chaque question repartirait
        de zero et "et pour /var ?" n'aurait aucun sens pour le modele.

        `incident` fait basculer le tour en mode investigation : le ticket est
        injecte dans le prompt, et les actions proposees lui sont rattachees.
        """
        context = retriever.retrieve(
            collection_name=self.rag_collection, question=user_message, n_results=3
        )
        now = datetime.now().astimezone().strftime("%A %d %B %Y, %H:%M (%Z)")
        messages: list[dict] = [
            {"role": "system", "content": f"""{STORAGE_SYSTEM_PROMPT}

Current server date and time: {now}. The model has no other source of time:
without this line it would answer that it does not know what time it is.

Use MCP only for current storage information. The tools that change the VM
(run_backup, create_snapshot, restore_from_backup) never execute from the chat:
calling one records an action proposal that the engineer confirms with a click.
So call them normally when you want to propose one, but never copy a tool call
as JSON into your answer -- written that way it creates nothing. And never say
a remediation has been launched: it is waiting on a human decision.
RAG documentation:
{context or 'No relevant internal documentation found.'}
{incident.as_prompt_block() if incident else ''}"""},
        ]
        # Seuls les tours texte sont rejoues : les appels d'outils d'une
        # conversation precedente ne sont pas rejouables (leurs resultats ne
        # sont plus a jour), le modele les redemande s'il en a besoin.
        for previous in history or []:
            if previous.get("role") in ("user", "assistant") and previous.get("content"):
                messages.append({"role": previous["role"], "content": previous["content"]})
        messages.append({"role": "user", "content": user_message})

        detected_tickets: list[dict] = []
        proposed_action_ids: list[uuid.UUID] = []
        final_text: str | None = None
        correlation_id = uuid.uuid4()

        # Session dédiée à l'audit des appels MCP, ouverte pour toute la boucle
        # d'outils : tous les appels d'une même conversation partagent ainsi le
        # même correlation_id. Sans created_by on ne sait pas à qui imputer
        # l'appel -- on n'audite pas, plutôt que d'inventer un utilisateur.
        audit_db = SessionLocal() if created_by is not None else None

        try:
            async with StorageMCPClient() as mcp:
                tools = await mcp.list_tools_for_llm()
                for _ in range(_MAX_TOOL_ROUNDS):
                    reply = groq_client.chat_with_tools(messages, tools)
                    if not reply.tool_calls:
                        final_text = reply.content or "I could not produce an answer."
                        break

                    messages.append({
                        "role": "assistant", "content": reply.content or "",
                        "tool_calls": [{
                            "id": call.id, "type": "function",
                            "function": {
                                "name": call.function.name, "arguments": call.function.arguments,
                            },
                        } for call in reply.tool_calls],
                    })

                    for call in reply.tool_calls:
                        name = call.function.name
                        try:
                            arguments = json.loads(call.function.arguments or "{}")
                            if not isinstance(arguments, dict):
                                arguments = {}
                        except json.JSONDecodeError:
                            arguments = {}

                        if name in REMEDIATION_TOOLS:
                            if audit_db is None:
                                # Sans utilisateur, la proposition n'aurait ni
                                # demandeur ni destinataire : on refuse plutot
                                # que de l'attribuer a quelqu'un au hasard.
                                result = {
                                    "status": "denied",
                                    "reason": "confirmation_required",
                                    "message": "Sensitive action not executed from the chat.",
                                }
                            else:
                                result, action_id = self._propose_action(
                                    audit_db,
                                    tool_name=name,
                                    arguments=arguments,
                                    created_by=created_by,
                                    incident=incident,
                                )
                                if action_id is not None:
                                    proposed_action_ids.append(action_id)
                        else:
                            try:
                                result = await mcp.call_tool(
                                    name,
                                    db=audit_db,
                                    user_id=created_by,
                                    correlation_id=correlation_id,
                                    **arguments,
                                )
                            except RuntimeError as error:
                                result = {"status": "error", "message": str(error)}

                        detected_tickets.extend(evaluate_tool_result(name, result))

                        messages.append({
                            "role": "tool", "tool_call_id": call.id,
                            "content": json.dumps(result, ensure_ascii=False),
                        })
        finally:
            if audit_db is not None:
                audit_db.close()

        if final_text is None:
            final = groq_client.chat_with_tools(messages)
            final_text = final.content or "MCP collection limit reached; try a more targeted question."

        # --- Rattrapage d'un appel d'outil ecrit au lieu d'etre emis ---------
        # La session d'audit est deja fermee a ce stade : on en ouvre une pour
        # ce seul enregistrement, comme le fait la creation de tickets.
        if not proposed_action_ids and incident is not None and created_by is not None:
            recovered = _recover_written_call(final_text, incident)
            if recovered is not None:
                tool_name, arguments = recovered
                try:
                    with SessionLocal() as db:
                        _, action_id = self._propose_action(
                            db,
                            tool_name=tool_name,
                            arguments=arguments,
                            created_by=created_by,
                            incident=incident,
                        )
                    if action_id is not None:
                        proposed_action_ids.append(action_id)
                        logger.info(
                            "Appel d'outil recupere depuis la reponse : %s sur %s",
                            tool_name, incident.ticket_number,
                        )
                except Exception:
                    logger.exception("Echec du rattrapage d'un appel d'outil ecrit en texte")

        # --- Creation automatique des tickets detectes -----------------------
        # SessionLocal est sync -> pas de "async with", pas de "await" sur
        # les appels incident_service.
        if detected_tickets and created_by is not None:
            try:
                with SessionLocal() as db:
                    for ticket_data in detected_tickets:
                        incident_service.create_ticket_from_diagnosis(
                            db,
                            created_by=created_by,
                            correlation_id=correlation_id,
                            **ticket_data,
                        )
            except Exception:
                logger.exception("Echec de la creation automatique d'un ticket d'incident")
        elif detected_tickets and created_by is None:
            logger.warning(
                "Anomalie(s) detectee(s) mais aucun created_by fourni -- "
                "ticket(s) non cree(s): %s",
                [t["title"] for t in detected_tickets],
            )

        return AgentTurn(text=final_text, proposed_action_ids=proposed_action_ids)


storage_persona = StoragePersona()

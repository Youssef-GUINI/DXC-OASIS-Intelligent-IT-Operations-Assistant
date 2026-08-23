import json
import logging

from groq import NotFoundError, RateLimitError

from app.llm.groq_client import groq_client
from app.rag.query_pipeline import get_context_for_query

logger = logging.getLogger(__name__)


class BasePersona:
    name: str = "base"
    system_prompt: str = "Tu es un assistant technique."
    rag_collection: str | None = None
    mcp_client = None
    tools_schema: list | None = None
    db_tools: dict | None = None  # {"nom_outil": fonction(db, **kwargs)}

    def build_system_message(self, user_message: str) -> str:
        context = ""
        if self.rag_collection:
            try:
                context = get_context_for_query(self.rag_collection, user_message)
            except Exception:
                context = ""

        if context:
            return (
                f"{self.system_prompt}\n\n"
                f"Voici des extraits de documentation technique pertinents :\n"
                f"{context}\n\n"
                f"Utilise ce contexte quand il est pertinent, et utilise les "
                f"outils disponibles quand la question necessite des donnees "
                f"reelles du systeme ou de l'historique des incidents."
            )
        return self.system_prompt

    def handle_message(self, user_message: str, db=None) -> str:
        system_message = self.build_system_message(user_message)

        if not self.tools_schema:
            try:
                return groq_client.chat(user_message, system_prompt=system_message)
            except (NotFoundError, RateLimitError) as exc:
                logger.warning("LLM chat unavailable for persona %s: %s", self.name, exc.__class__.__name__)
                return self._tool_aware_offline_fallback(user_message, exc, db)
            except Exception as exc:
                logger.exception("LLM chat failed for persona %s", self.name)
                return self._tool_aware_offline_fallback(user_message, exc, db)

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ]

        for _ in range(6):
            try:
                message = groq_client.chat_with_tools(messages, self.tools_schema)
            except (NotFoundError, RateLimitError) as exc:
                logger.warning("LLM tool chat unavailable for persona %s: %s", self.name, exc.__class__.__name__)
                return self._tool_aware_offline_fallback(user_message, exc, db)
            except Exception as exc:
                logger.exception("LLM tool chat failed for persona %s", self.name)
                return self._tool_aware_offline_fallback(user_message, exc, db)

            if not message.tool_calls:
                return message.content

            messages.append(
                {
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [tc.model_dump() for tc in message.tool_calls],
                }
            )

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments or "{}")

                result = self._execute_tool(tool_name, tool_args, db)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result),
                    }
                )

        return self._finalize_from_tool_results(messages, user_message)

    def _finalize_from_tool_results(self, messages: list, user_message: str) -> str:
        tool_results = [
            message["content"]
            for message in messages
            if message.get("role") == "tool"
        ]
        if not tool_results:
            return self._offline_fallback(user_message, RuntimeError("ToolLoopWithoutResults"))

        summary_prompt = (
            "Tu as deja appele plusieurs outils. Maintenant, n'appelle plus aucun outil.\n"
            "Redige une reponse finale courte, claire et actionnable pour l'utilisateur.\n\n"
            f"Question utilisateur : {user_message}\n\n"
            "Resultats outils disponibles :\n"
            + "\n".join(tool_results[-8:])
        )

        try:
            return groq_client.chat(summary_prompt, system_prompt=self.system_prompt)
        except (NotFoundError, RateLimitError) as exc:
            logger.warning("LLM finalization unavailable for persona %s: %s", self.name, exc.__class__.__name__)
            return self._local_tool_summary(tool_results, user_message)
        except Exception as exc:
            logger.exception("LLM finalization failed for persona %s", self.name)
            return self._local_tool_summary(tool_results, user_message)

    def _local_tool_summary(self, tool_results: list[str], user_message: str) -> str:
        parsed_results = []
        for raw in tool_results[-8:]:
            try:
                parsed_results.append(json.loads(raw))
            except json.JSONDecodeError:
                parsed_results.append(raw)

        return (
            "J'ai recupere les donnees disponibles via les outils Linux, mais le LLM n'a pas pu produire "
            "une synthese finale. Voici le contexte brut utile pour continuer le diagnostic :\n\n"
            f"Question : {user_message}\n\n"
            f"{json.dumps(parsed_results, ensure_ascii=False, indent=2)}"
        )

    def _tool_aware_offline_fallback(self, user_message: str, exc: Exception, db=None) -> str:
        tool_names = self._select_offline_tools(user_message)
        if not tool_names:
            small_talk = self._small_talk_offline_response(user_message, exc)
            if small_talk:
                return small_talk
            return self._offline_fallback(user_message, exc)

        results = []
        for tool_name in tool_names:
            results.append((tool_name, self._execute_tool(tool_name, {}, db)))

        return self._format_offline_tool_response(user_message, exc, results)

    def _select_offline_tools(self, user_message: str) -> list[str]:
        if not self.tools_schema:
            return []

        lower = user_message.lower()
        requested = []

        def add(tool_name: str) -> None:
            if any(tool["function"]["name"] == tool_name for tool in self.tools_schema) and tool_name not in requested:
                requested.append(tool_name)

        asks_overview = any(
            word in lower
            for word in [
                "etat",
                "status",
                "sante",
                "health",
                "dashboard",
                "diagnostic",
                "check",
                "tout",
                "global",
            ]
        )
        asks_incidents = "incident" in lower or "alerte" in lower or "alert" in lower

        if "cpu" in lower or "processeur" in lower or "charge" in lower or "load" in lower or asks_overview:
            add("get_cpu_usage")
        if "ram" in lower or "memoire" in lower or "memory" in lower or asks_overview:
            add("get_ram_usage")
        if "disk" in lower or "disque" in lower or "stockage" in lower or "storage" in lower or "/var" in lower or asks_overview:
            add("get_disk_usage")
        if "service" in lower or "systemctl" in lower or "nginx" in lower or "docker" in lower or asks_overview:
            add("get_services_status")
        if "network" in lower or "reseau" in lower or "latence" in lower or "ping" in lower or asks_overview:
            add("check_network")
        if asks_incidents:
            add("get_recent_incidents")

        return requested

    def _small_talk_offline_response(self, user_message: str, exc: Exception) -> str | None:
        lower = user_message.lower().strip()
        compact = lower.replace("?", "").replace("!", "").replace(".", "").replace(",", "")
        words = set(compact.split())
        greetings = {"bonjour", "salut", "hello", "hi", "salam", "bonsoir", "cv", "ca", "va"}

        if compact and words.issubset(greetings):
            return (
                "Bonjour ! Oui, ca va. Je suis pret a t'aider sur Linux, les incidents, "
                "le CPU, la RAM, le disque, les services ou le reseau.\n\n"
                f"Note technique : le LLM externe est actuellement limite ({exc.__class__.__name__}), "
                "donc je peux continuer en mode local avec les outils OASIS."
            )

        return None

    def _format_offline_tool_response(self, user_message: str, exc: Exception, results: list[tuple[str, dict]]) -> str:
        reason = exc.__class__.__name__
        lines = [
            "Le service LLM externe est limite pour le moment, mais j'ai utilise les outils locaux OASIS.",
            f"Cause technique detectee : {reason}.",
            "",
            "Etat recupere :",
        ]

        has_error = False
        risk_notes = []

        for tool_name, payload in results:
            if "error" in payload:
                has_error = True
                lines.append(f"- {tool_name}: indisponible ({payload['error']})")
                continue

            data = payload.get("result", payload)
            if tool_name == "get_cpu_usage":
                usage = data.get("usage_percent")
                lines.append(
                    f"- CPU: {usage}% utilise, top process: {data.get('top_process', 'n/a')}, coeurs: {data.get('cores', 'n/a')}."
                )
                if isinstance(usage, (int, float)) and usage >= 85:
                    risk_notes.append("CPU eleve: verifier `top` et `ps aux --sort=-%cpu | head -10`.")
            elif tool_name == "get_ram_usage":
                usage = data.get("usage_percent")
                lines.append(
                    f"- RAM: {data.get('used_gb', 'n/a')} GB / {data.get('total_gb', 'n/a')} GB ({usage}%)."
                )
                if isinstance(usage, (int, float)) and usage >= 85:
                    risk_notes.append("RAM elevee: verifier `free -h`, `vmstat 1 5` et les processus par memoire.")
            elif tool_name == "get_disk_usage":
                usage = data.get("usage_percent")
                lines.append(
                    f"- Disque {data.get('mount_point', '/')}: {data.get('used_gb', 'n/a')} GB / {data.get('total_gb', 'n/a')} GB ({usage}%)."
                )
                if isinstance(usage, (int, float)) and usage >= 85:
                    risk_notes.append("Disque eleve: verifier `df -h` puis les gros dossiers avec `du -xh /var | sort -h | tail -20`.")
            elif tool_name == "get_services_status":
                lines.append(f"- Services: {json.dumps(data, ensure_ascii=False)}.")
                failed_services = [service for service, status in data.items() if status == "failed"] if isinstance(data, dict) else []
                if failed_services:
                    risk_notes.append(
                        "Service(s) en echec: "
                        + ", ".join(failed_services)
                        + ". Verifier `systemctl status <service>` avant redemarrage."
                    )
            elif tool_name == "check_network":
                lines.append(
                    f"- Reseau: interface {data.get('interface_status', 'n/a')}, latence {data.get('latency_ms', 'n/a')} ms, perte {data.get('packet_loss_percent', 'n/a')}%."
                )
                loss = data.get("packet_loss_percent")
                if isinstance(loss, (int, float)) and loss > 1:
                    risk_notes.append("Perte reseau notable: verifier l'interface, DNS et passerelle.")
            elif tool_name == "get_recent_incidents":
                incidents = data if isinstance(data, list) else []
                lines.append(f"- Incidents recents: {len(incidents)} element(s) retournes.")
                for incident in incidents[:5]:
                    lines.append(
                        f"  - #{incident.get('id', 'n/a')} {incident.get('category', 'n/a')} / {incident.get('severity', 'n/a')} / {incident.get('status', 'n/a')}"
                    )
            else:
                lines.append(f"- {tool_name}: {json.dumps(data, ensure_ascii=False)}")

        lines.append("")
        if risk_notes:
            lines.append("Actions recommandees :")
            lines.extend(f"- {note}" for note in risk_notes)
        elif has_error:
            lines.append("Certains outils locaux n'ont pas repondu. Verifie les logs backend et le serveur MCP local.")
        else:
            lines.append("Aucune anomalie critique evidente dans ces donnees locales. Continue avec les incidents ouverts si le dashboard signale un probleme.")

        return "\n".join(lines)

    def _offline_fallback(self, user_message: str, exc: Exception) -> str:
        lower = user_message.lower()
        reason = exc.__class__.__name__

        if "cpu" in lower or "100" in lower or "charge" in lower or "load" in lower:
            guidance = (
                "1. Verifie les processus les plus consommateurs : `top` ou `ps aux --sort=-%cpu | head -10`.\n"
                "2. Controle la charge systeme : `uptime`, puis compare load average avec le nombre de CPU : `nproc`.\n"
                "3. Regarde les erreurs recentes : `journalctl -p warning..alert --since \"30 min ago\"`.\n"
                "4. Si un service est responsable, inspecte-le avec `systemctl status <service>` avant de redemarrer."
            )
        elif "ram" in lower or "memory" in lower or "memoire" in lower:
            guidance = (
                "1. Controle la memoire : `free -h`.\n"
                "2. Liste les processus : `ps aux --sort=-%mem | head -10`.\n"
                "3. Verifie le swap : `swapon --show` et `vmstat 1 5`.\n"
                "4. Si la pression continue, identifie le service fautif avant toute action."
            )
        elif "disk" in lower or "disque" in lower or "/var" in lower:
            guidance = (
                "1. Verifie l'espace disque : `df -h`.\n"
                "2. Trouve les gros dossiers : `du -xh /var | sort -h | tail -20`.\n"
                "3. Controle les logs : `journalctl --disk-usage` et l'etat de logrotate.\n"
                "4. Nettoie uniquement les fichiers identifies comme temporaires ou logs archives."
            )
        else:
            guidance = (
                "1. Recupere l'etat general : `uptime`, `free -h`, `df -h`.\n"
                "2. Consulte les erreurs recentes : `journalctl -p warning..alert --since \"1 hour ago\"`.\n"
                "3. Verifie les services critiques : `systemctl --failed`.\n"
                "4. Ouvre la page Incidents pour comparer avec l'historique backend."
            )

        return (
            "Le service AI externe est momentanement indisponible, donc je passe en mode diagnostic local.\n"
            f"Cause technique detectee : {reason}.\n\n"
            f"{guidance}"
        )

    def _execute_tool(self, tool_name: str, tool_args: dict, db) -> dict:
        if self.db_tools and tool_name in self.db_tools:
            if db is None:
                return {"error": "Base de donnees non disponible pour cet outil"}
            try:
                return {"result": self.db_tools[tool_name](db, **tool_args)}
            except Exception as exc:
                return {"error": str(exc)}

        if self.mcp_client:
            try:
                return {"result": self.mcp_client.call(tool_name, tool_args)}
            except Exception as exc:
                return {"error": str(exc)}

        return {"error": f"Outil inconnu : {tool_name}"}

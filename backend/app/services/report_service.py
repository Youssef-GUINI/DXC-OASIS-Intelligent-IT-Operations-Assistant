"""
app/services/report_service.py

Génère les rapports PDF : un rapport global de l'environnement Storage, et un
rapport détaillé par incident.

Les rapports sont construits avec ReportLab et non WeasyPrint, bien que ce
dernier figure dans requirements.txt : WeasyPrint s'appuie sur les
bibliothèques GTK (libgobject, pango, cairo) qui ne sont pas installées avec
pip sous Windows, et son import échoue sur le poste de développement.

Aucune donnée n'est inventée ici. Le rapport reprend ce que les tools MCP ont
lu sur la VM au moment de la génération ; quand une information manque, il
l'écrit noir sur blanc plutôt que de laisser une case vide.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.orm import Session

from app.dashboard import kpi_service
from app.models.incident_ticket import IncidentStatus, IncidentTicket
from app.services import incident_service

# Palette alignée sur l'interface (brand indigo, statuts vert/ambre/rouge).
_BRAND = colors.HexColor("#4f46e5")
_INK = colors.HexColor("#0f172a")
_MUTED = colors.HexColor("#64748b")
_LINE = colors.HexColor("#e2e8f0")
_ZEBRA = colors.HexColor("#f8fafc")

_STATUS_COLORS = {
    "healthy": colors.HexColor("#16a34a"),
    "success": colors.HexColor("#16a34a"),
    "resolved": colors.HexColor("#16a34a"),
    "closed": colors.HexColor("#16a34a"),
    "warning": colors.HexColor("#d97706"),
    "medium": colors.HexColor("#d97706"),
    "scheduled": _MUTED,
    "running": _BRAND,
    "in_progress": _BRAND,
    "critical": colors.HexColor("#dc2626"),
    "failed": colors.HexColor("#dc2626"),
    "high": colors.HexColor("#ea580c"),
    "open": colors.HexColor("#dc2626"),
    "unknown": _MUTED,
    "à confirmer": colors.HexColor("#d97706"),
    "proposée": _MUTED,
}


# --------------------------------------------------------------------------
# Styles et briques de mise en page
# --------------------------------------------------------------------------

def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "OasisTitle", parent=base["Title"], fontSize=20, leading=24,
            textColor=_INK, alignment=TA_LEFT, spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "OasisSubtitle", parent=base["Normal"], fontSize=10, leading=14,
            textColor=_MUTED, spaceAfter=14,
        ),
        "section": ParagraphStyle(
            "OasisSection", parent=base["Heading2"], fontSize=13, leading=16,
            textColor=_BRAND, spaceBefore=16, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "OasisBody", parent=base["Normal"], fontSize=9.5, leading=13,
            textColor=_INK,
        ),
        "muted": ParagraphStyle(
            "OasisMuted", parent=base["Normal"], fontSize=9, leading=12,
            textColor=_MUTED,
        ),
        "cell": ParagraphStyle(
            "OasisCell", parent=base["Normal"], fontSize=8.5, leading=11,
            textColor=_INK,
        ),
    }


def _table(rows: list[list[Any]], widths: list[float], *, status_column: int | None = None) -> Table:
    """
    Tableau à en-tête coloré et lignes alternées.

    `status_column` colore le texte d'une colonne selon la valeur du statut :
    un job en échec ou un volume saturé se repère alors sans lire la ligne.
    """
    table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), _BRAND),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.4, _LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    for index in range(1, len(rows)):
        if index % 2 == 0:
            style.append(("BACKGROUND", (0, index), (-1, index), _ZEBRA))
        if status_column is not None:
            value = str(rows[index][status_column]).strip().lower()
            colour = _STATUS_COLORS.get(value)
            if colour is not None:
                style.append(("TEXTCOLOR", (status_column, index), (status_column, index), colour))
                style.append(
                    ("FONTNAME", (status_column, index), (status_column, index), "Helvetica-Bold")
                )
    table.setStyle(TableStyle(style))
    return table


def _footer(canvas, document) -> None:
    """Pied de page : origine du document et numéro de page."""
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(_MUTED)
    canvas.drawString(
        18 * mm, 12 * mm,
        "OASIS — Rapport généré automatiquement à partir des données lues sur l'environnement Storage.",
    )
    canvas.drawRightString(A4[0] - 18 * mm, 12 * mm, f"Page {canvas.getPageNumber()}")
    canvas.setStrokeColor(_LINE)
    canvas.line(18 * mm, 15 * mm, A4[0] - 18 * mm, 15 * mm)
    canvas.restoreState()


def _render(story: list, title: str) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=20 * mm,
        title=title, author="OASIS",
    )
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def _header(story: list, styles: dict, title: str, subtitle: str, author: str | None) -> None:
    generated_at = datetime.now(timezone.utc).strftime("%d/%m/%Y à %H:%M UTC")
    story.append(Paragraph(title, styles["title"]))
    story.append(Paragraph(
        f"Rapport généré automatiquement le {generated_at}"
        + (f" — demandé par {author}" if author else "")
        + f"<br/>{subtitle}",
        styles["subtitle"],
    ))


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return "-"
    return value.strftime("%d/%m/%Y %H:%M")


def _as_utc(value: datetime | None) -> datetime | None:
    """
    Ramène une date à un datetime aware.

    Les colonnes sont déclarées `timezone=True`, mais un ticket résolu dans la
    même session porte encore le `datetime.utcnow()` naïf écrit par
    `incident_service` : les soustraire ferait lever un TypeError au moment où
    l'ingénieur télécharge le rapport.
    """
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _format_duration(delta: timedelta) -> str:
    minutes = max(int(delta.total_seconds() // 60), 0)
    if minutes < 60:
        return f"{minutes} min"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours} h {minutes:02d}"
    days, hours = divmod(hours, 24)
    return f"{days} j {hours} h"


def _resolution_text(ticket: IncidentTicket) -> str:
    """
    Contenu de la case « Résolu le ».

    Un tiret ne disait pas si l'incident était encore ouvert ou si la date
    manquait : la case porte désormais l'état réel, et le délai — temps de
    résolution pour un ticket fermé, ancienneté pour un ticket ouvert.
    """
    created = _as_utc(ticket.created_at)
    resolved = _as_utc(ticket.resolved_at)

    if resolved is not None:
        text = _format_datetime(ticket.resolved_at)
        if created is not None:
            text += (
                f"<br/><font size='7.5' color='#64748b'>"
                f"Résolu en {_format_duration(resolved - created)}</font>"
            )
        return text

    if ticket.status == IncidentStatus.CLOSED:
        label = "Clôturé sans date de résolution"
    elif ticket.status == IncidentStatus.IN_PROGRESS:
        label = "Non résolu — traitement en cours"
    else:
        label = "Non résolu — ticket ouvert"

    if created is not None:
        label += (
            f"<br/><font size='7.5' color='#64748b'>"
            f"Ouvert depuis {_format_duration(datetime.now(timezone.utc) - created)}</font>"
        )
    return label


def _derived_root_cause(ticket: IncidentTicket) -> str | None:
    """
    Cause racine provisoire, reconstituée à partir des mesures du ticket.

    `root_cause` n'est écrit que par la passe de synthèse de l'investigation :
    tant qu'aucun ingénieur n'a lancé le diagnostic, le rapport annonçait une
    cause « non établie » alors que la mesure qui a ouvert l'incident, elle,
    est connue et stockée. On la restitue telle quelle, sans l'interpréter, et
    le rapport précise juste en dessous que c'est un constat d'ouverture et non
    une analyse. Retourne None quand les données ne permettent rien d'affirmer.
    """
    data = ticket.mcp_data if isinstance(ticket.mcp_data, dict) else {}

    job_id = data.get("job_id")
    if job_id and str(data.get("status", "")).strip().lower() == "failed":
        detail = f" (résultat systemd : {data['error_code']})" if data.get("error_code") else ""
        text = f"Le job de sauvegarde {job_id} s'est terminé en échec{detail}"
        target = data.get("target")
        if target:
            text += f", sur la cible {target}"
        last_run = str(data.get("last_run") or "")[:16].replace("T", " ")
        if last_run:
            text += f", lors de l'exécution du {last_run}"
        return text + "."

    percent = data.get("percent_used")
    if percent is not None:
        volume = data.get("volume_id") or data.get("mountpoint") or ticket.affected_system
        text = f"Le volume {volume} atteint {percent}% d'occupation"
        if data.get("used_gb") is not None and data.get("total_gb") is not None:
            text += f" ({data['used_gb']} / {data['total_gb']} Go)"
        if data.get("mountpoint") and data.get("mountpoint") != volume:
            text += f", monté sur {data['mountpoint']}"
        return text + "."

    return None


def _escape(value: Any) -> str:
    """Neutralise les chevrons : ReportLab interprète le HTML dans Paragraph."""
    text = "-" if value is None else str(value)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _recommendation_text(item: Any, styles: dict) -> str:
    """
    Rend une recommandation lisible.

    L'agent les enregistre en objets (`description`, `action_type`, `target`).
    Les afficher en JSON brut donnerait un rapport illisible : on sort la phrase,
    et on rappelle discrètement l'action et sa cible.
    """
    if not isinstance(item, dict):
        return _escape(item)

    description = item.get("description") or item.get("action") or item.get("title")
    if not description:
        # Objet d'une forme inattendue : mieux vaut le montrer que le perdre.
        return _escape(json.dumps(item, ensure_ascii=False))

    context = " · ".join(
        str(item[key]) for key in ("action_type", "target") if item.get(key)
    )
    text = _escape(description)
    if context:
        text += f"<br/><font size='7.5' color='#64748b'>{_escape(context)}</font>"
    return text


# --------------------------------------------------------------------------
# Rapport global
# --------------------------------------------------------------------------

def build_global_report(db: Session, *, author: str | None = None) -> bytes:
    """
    Rapport de l'environnement complet : synthèse, alertes, capacité,
    sauvegardes et incidents.
    """
    overview = kpi_service.get_overview(db)
    styles = _styles()
    story: list = []

    _header(
        story, styles,
        "Environnement Storage &amp; Backup",
        "Capacité, sauvegardes et incidents de l'environnement supervisé par OASIS.",
        author,
    )

    # --- Synthèse ---------------------------------------------------------
    status = overview.get("overall_status", "unknown")
    score = overview.get("health_score")
    capacity = overview.get("capacity", {})
    backups = overview.get("backups", {})
    incidents = overview.get("incidents", {})

    story.append(Paragraph("Synthèse", styles["section"]))
    story.append(_table(
        [
            ["État général", "Score de santé", "Capacité utilisée", "Sauvegardes", "Incidents ouverts"],
            [
                status.upper(),
                f"{score}/100" if score is not None else "indisponible",
                f"{capacity.get('percent_used', 0)}%"
                f" ({capacity.get('used_gb', 0)} / {capacity.get('total_gb', 0)} Go)",
                f"{backups.get('successful', 0)} OK / {backups.get('failed', 0)} en échec"
                f" / {backups.get('scheduled', 0)} planifiées",
                str(incidents.get("open", 0)),
            ],
        ],
        [32 * mm, 26 * mm, 44 * mm, 46 * mm, 26 * mm],
        status_column=0,
    ))
    headline = overview.get("headline")
    if headline:
        story.append(Spacer(1, 6))
        story.append(Paragraph(_escape(headline), styles["body"]))

    # --- Alertes ----------------------------------------------------------
    story.append(Paragraph("Alertes actives", styles["section"]))
    alerts = overview.get("alerts", [])
    if alerts:
        rows = [["Sévérité", "Type", "Cible", "Message"]]
        rows += [
            [
                alert.get("severity", "-"),
                alert.get("type", "-"),
                Paragraph(_escape(alert.get("target")), styles["cell"]),
                Paragraph(_escape(alert.get("message")), styles["cell"]),
            ]
            for alert in alerts
        ]
        story.append(_table(rows, [22 * mm, 32 * mm, 44 * mm, 76 * mm], status_column=0))
    else:
        story.append(Paragraph("Aucune alerte active au moment de la génération.", styles["muted"]))

    # --- Capacité ---------------------------------------------------------
    story.append(Paragraph("Capacité des volumes", styles["section"]))
    if capacity.get("error"):
        story.append(Paragraph(
            f"Environnement injoignable : {_escape(capacity['error'])}", styles["muted"],
        ))
    elif capacity.get("volumes"):
        rows = [["Volume", "Point de montage", "Système", "Taille", "Utilisé", "%", "État"]]
        rows += [
            [
                Paragraph(_escape(volume.get("volume_id")), styles["cell"]),
                Paragraph(_escape(volume.get("mountpoint")), styles["cell"]),
                volume.get("filesystem", "-"),
                f"{volume.get('total_gb', 0)} Go",
                f"{volume.get('used_gb', 0)} Go",
                f"{volume.get('percent_used', 0)}%",
                volume.get("status", "-"),
            ]
            for volume in capacity["volumes"]
        ]
        story.append(_table(
            rows, [34 * mm, 42 * mm, 16 * mm, 18 * mm, 18 * mm, 13 * mm, 22 * mm],
            status_column=6,
        ))
        story.append(Spacer(1, 5))
        story.append(Paragraph(
            f"Total : {capacity.get('used_gb', 0)} Go utilisés sur {capacity.get('total_gb', 0)} Go, "
            f"{capacity.get('available_gb', 0)} Go disponibles, "
            f"{capacity.get('reserved_gb', 0)} Go réservés au superutilisateur. "
            f"{capacity.get('volumes_near_limit', 0)} volume(s) au-delà du seuil d'alerte.",
            styles["muted"],
        ))
    else:
        story.append(Paragraph("Aucun volume remonté.", styles["muted"]))

    # --- Sauvegardes ------------------------------------------------------
    story.append(Paragraph("Jobs de sauvegarde", styles["section"]))
    if backups.get("error"):
        story.append(Paragraph(
            f"Jobs illisibles : {_escape(backups['error'])}", styles["muted"],
        ))
    elif not backups.get("configured"):
        story.append(Paragraph(
            "Aucun job de sauvegarde n'est configuré sur l'environnement.", styles["muted"],
        ))
    else:
        rows = [["Job", "Cible", "Statut", "Dernière exécution", "Depuis"]]
        for job in backups.get("jobs", []):
            hours = job.get("hours_since_last_success", 0)
            rows.append([
                Paragraph(_escape(job.get("job_id")), styles["cell"]),
                Paragraph(_escape(job.get("target")), styles["cell"]),
                job.get("status", "-"),
                (job.get("last_run") or "jamais exécutée")[:16].replace("T", " "),
                f"{hours} h" if hours else "-",
            ])
        story.append(_table(
            rows, [40 * mm, 54 * mm, 22 * mm, 32 * mm, 15 * mm], status_column=2,
        ))

    # --- Incidents --------------------------------------------------------
    story.append(Paragraph("Incidents", styles["section"]))
    by_severity = incidents.get("by_severity", {})
    story.append(Paragraph(
        f"{incidents.get('open', 0)} incident(s) ouvert(s) - "
        f"critiques : {by_severity.get('critical', 0)}, élevés : {by_severity.get('high', 0)}, "
        f"moyens : {by_severity.get('medium', 0)}, faibles : {by_severity.get('low', 0)}. "
        f"{incidents.get('resolved_last_7d', 0)} résolu(s) ces 7 derniers jours.",
        styles["body"],
    ))
    story.append(Spacer(1, 8))

    open_tickets = incident_service.list_tickets(db, limit=50)
    open_tickets = [t for t in open_tickets if t.status in (IncidentStatus.OPEN, IncidentStatus.IN_PROGRESS)]
    if open_tickets:
        rows = [["Ticket", "Titre", "Sévérité", "Statut", "Système", "Ouvert le"]]
        rows += [
            [
                ticket.ticket_number,
                Paragraph(_escape(ticket.title), styles["cell"]),
                ticket.severity.value,
                ticket.status.value,
                Paragraph(_escape(ticket.affected_system), styles["cell"]),
                _format_datetime(ticket.created_at),
            ]
            for ticket in open_tickets
        ]
        story.append(_table(
            rows, [24 * mm, 50 * mm, 18 * mm, 22 * mm, 32 * mm, 26 * mm], status_column=2,
        ))
    else:
        story.append(Paragraph("Aucun incident ouvert.", styles["muted"]))

    return _render(story, "OASIS - Rapport Storage & Backup")


# --------------------------------------------------------------------------
# Rapport d'incident
# --------------------------------------------------------------------------

def build_incident_report(
    db: Session, ticket_id: uuid.UUID, *, author: str | None = None,
) -> bytes | None:
    """Rapport détaillé d'un incident. Retourne None si le ticket n'existe pas."""
    ticket: IncidentTicket | None = incident_service.get_ticket(db, ticket_id)
    if ticket is None:
        return None

    styles = _styles()
    story: list = []

    _header(
        story, styles,
        f"Incident {_escape(ticket.ticket_number)}",
        _escape(ticket.title),
        author,
    )

    # --- Identité ---------------------------------------------------------
    story.append(Paragraph("Fiche", styles["section"]))
    story.append(_table(
        [
            ["Sévérité", "Statut", "Système concerné", "Ouvert le", "Résolu le"],
            [
                ticket.severity.value,
                ticket.status.value,
                Paragraph(_escape(ticket.affected_system), styles["cell"]),
                _format_datetime(ticket.created_at),
                Paragraph(_resolution_text(ticket), styles["cell"]),
            ],
        ],
        [24 * mm, 26 * mm, 44 * mm, 26 * mm, 40 * mm],
        status_column=0,
    ))

    # --- Analyse ----------------------------------------------------------
    # La cause racine établie est celle de l'investigation. À défaut, le rapport
    # rend le constat qui a ouvert l'incident plutôt qu'une case vide -- en
    # disant lequel des deux il montre.
    derived_cause = None if ticket.root_cause else _derived_root_cause(ticket)
    cause_note = (
        None if ticket.root_cause
        else "Constat relevé sur l'environnement à l'ouverture de l'incident. "
             "Le diagnostic détaillé n'a pas encore été mené : cette cause reste "
             "à confirmer par l'investigation."
    )

    for heading, value, fallback, note in (
        ("Description", ticket.description, "Aucune description.", None),
        (
            "Cause racine",
            ticket.root_cause or derived_cause,
            "Cause racine non établie à ce jour.",
            cause_note,
        ),
        ("Impact", ticket.impact_summary, "Impact non renseigné.", None),
    ):
        story.append(Paragraph(heading, styles["section"]))
        story.append(Paragraph(
            _escape(value) if value else fallback,
            styles["body"] if value else styles["muted"],
        ))
        if value and note:
            story.append(Spacer(1, 4))
            story.append(Paragraph(note, styles["muted"]))

    # --- Recommandations --------------------------------------------------
    story.append(Paragraph("Recommandations", styles["section"]))
    recommendations = ticket.recommendations or []
    if recommendations:
        rows = [["#", "Recommandation"]]
        for index, item in enumerate(recommendations, start=1):
            rows.append([str(index), Paragraph(_recommendation_text(item, styles), styles["cell"])])
        story.append(_table(rows, [10 * mm, 154 * mm]))
    else:
        story.append(Paragraph("Aucune recommandation enregistrée.", styles["muted"]))

    # --- Actions ----------------------------------------------------------
    story.append(Paragraph("Actions demandées", styles["section"]))
    actions = list(ticket.action_requests or [])
    if actions:
        rows = [["Action", "Cible", "Statut", "Demandée le", "Terminée le"]]
        rows += [
            [
                Paragraph(_escape(action.action_type), styles["cell"]),
                Paragraph(_escape(action.target), styles["cell"]),
                action.status.value,
                _format_datetime(action.created_at),
                _format_datetime(action.completed_at),
            ]
            for action in actions
        ]
        story.append(_table(
            rows, [40 * mm, 44 * mm, 24 * mm, 28 * mm, 28 * mm], status_column=2,
        ))
    else:
        # Aucune action n'a encore été demandée : le rapport montre alors les
        # remédiations que l'agent a proposées et qui attendent une décision.
        # C'est l'information utile à qui lit le rapport pour savoir quoi faire.
        proposed = [
            item for item in (ticket.recommendations or [])
            if isinstance(item, dict) and item.get("action_type")
        ]
        if proposed:
            story.append(Paragraph(
                "Aucune action n'a encore été exécutée. Les remédiations ci-dessous "
                "ont été proposées par OASIS et attendent la décision d'un ingénieur.",
                styles["muted"],
            ))
            story.append(Spacer(1, 6))
            rows = [["Action proposée", "Cible", "Statut"]]
            rows += [
                [
                    Paragraph(_escape(item.get("action_type")), styles["cell"]),
                    Paragraph(_escape(item.get("target") or ticket.affected_system), styles["cell"]),
                    "à confirmer" if item.get("requires_confirmation") else "proposée",
                ]
                for item in proposed
            ]
            story.append(_table(rows, [54 * mm, 80 * mm, 30 * mm], status_column=2))
        else:
            story.append(Paragraph(
                "Aucune action n'a été demandée sur cet incident, et aucune remédiation "
                "automatisable n'a été proposée.",
                styles["muted"],
            ))

    # --- Journal ----------------------------------------------------------
    story.append(Paragraph("Journal de traitement", styles["section"]))
    notes = sorted(ticket.notes or [], key=lambda note: note.created_at)
    if notes:
        rows = [["Date", "Note"]]
        rows += [
            [_format_datetime(note.created_at), Paragraph(_escape(note.content), styles["cell"])]
            for note in notes
        ]
        story.append(_table(rows, [30 * mm, 134 * mm]))
    else:
        story.append(Paragraph("Aucune note enregistrée.", styles["muted"]))

    # --- Preuves ----------------------------------------------------------
    # Les mesures brutes qui ont motivé le diagnostic. C'est ce qui distingue
    # un rapport vérifiable d'un résumé : le lecteur voit les données lues sur
    # la machine, pas seulement leur interprétation.
    if ticket.mcp_data:
        story.append(PageBreak())
        story.append(Paragraph("Données relevées sur l'environnement", styles["section"]))
        story.append(Paragraph(
            "Mesures lues par les outils MCP au moment du diagnostic.", styles["muted"],
        ))
        story.append(Spacer(1, 6))
        dump = json.dumps(ticket.mcp_data, ensure_ascii=False, indent=2, default=str)
        for chunk in dump.splitlines():
            story.append(Paragraph(
                f"<font face='Courier' size='7.5'>{_escape(chunk)}</font>", styles["cell"],
            ))

    return _render(story, f"OASIS - Incident {ticket.ticket_number}")

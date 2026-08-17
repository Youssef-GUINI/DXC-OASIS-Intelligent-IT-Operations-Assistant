import os
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

from app.models.incident import Incident

REPORTS_DIR = "generated_reports"


def generate_incident_report(incident: Incident, kpis: dict | None = None) -> str:
    os.makedirs(REPORTS_DIR, exist_ok=True)

    filename = f"incident_{incident.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleCustom", parent=styles["Title"], fontSize=18)
    heading_style = ParagraphStyle("HeadingCustom", parent=styles["Heading2"], spaceBefore=12, spaceAfter=6)
    body_style = styles["BodyText"]

    doc = SimpleDocTemplate(filepath, pagesize=A4)
    elements = []

    elements.append(Paragraph("Rapport d'incident — OASIS AI Copilot", title_style))
    elements.append(Spacer(1, 0.5 * cm))

    elements.append(Paragraph("Informations générales", heading_style))
    elements.append(Paragraph(f"<b>ID Incident :</b> {incident.id}", body_style))
    elements.append(Paragraph(f"<b>Persona :</b> {incident.persona}", body_style))
    elements.append(Paragraph(f"<b>Source :</b> {incident.source}", body_style))
    elements.append(Paragraph(f"<b>Catégorie :</b> {incident.category or 'N/A'}", body_style))
    elements.append(Paragraph(f"<b>Sévérité :</b> {incident.severity or 'N/A'}", body_style))
    elements.append(Paragraph(f"<b>Statut :</b> {incident.status}", body_style))
    elements.append(Paragraph(f"<b>Créé le :</b> {incident.created_at}", body_style))
    if incident.resolved_at:
        elements.append(Paragraph(f"<b>Résolu le :</b> {incident.resolved_at}", body_style))

    elements.append(Paragraph("Résumé de l'incident", heading_style))
    elements.append(Paragraph(incident.response.replace("\n", "<br/>"), body_style))

    if incident.diagnosis:
        elements.append(Paragraph("Diagnostic et recommandations (analyse IA)", heading_style))
        elements.append(Paragraph(incident.diagnosis.replace("\n", "<br/>"), body_style))

    if kpis:
        elements.append(Paragraph("Contexte global — Indicateurs Linux", heading_style))
        elements.append(Paragraph(
            "Ces chiffres reflètent l'état global du système Linux au moment "
            "de la génération de ce rapport, pour situer cet incident dans son contexte.",
            body_style,
        ))
        elements.append(Spacer(1, 0.3 * cm))

        table_data = [
            ["Indicateur", "Valeur"],
            ["Total incidents", str(kpis["total_incidents"])],
            ["Incidents ouverts", str(kpis["open_incidents"])],
            ["Incidents résolus", str(kpis["resolved_incidents"])],
            ["Temps moyen de résolution", f"{kpis['avg_resolution_minutes']} min" if kpis["avg_resolution_minutes"] else "N/A"],
        ]
        table = Table(table_data, colWidths=[8 * cm, 6 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
        ]))
        elements.append(table)

        elements.append(Spacer(1, 0.4 * cm))
        elements.append(Paragraph(
            f"<b>Répartition par catégorie :</b> "
            f"{', '.join(f'{k}: {v}' for k, v in kpis['incidents_by_category'].items())}",
            body_style,
        ))
        elements.append(Paragraph(
            f"<b>Répartition par sévérité :</b> "
            f"{', '.join(f'{k}: {v}' for k, v in kpis['incidents_by_severity'].items())}",
            body_style,
        ))

    doc.build(elements)
    return filepath

def generate_global_report(kpis: dict, open_incidents: list, resolved_incidents: list) -> str:
    os.makedirs(REPORTS_DIR, exist_ok=True)

    filename = f"rapport_global_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleCustom", parent=styles["Title"], fontSize=18)
    heading_style = ParagraphStyle("HeadingCustom", parent=styles["Heading2"], spaceBefore=14, spaceAfter=6)
    body_style = styles["BodyText"]
    small_style = ParagraphStyle("Small", parent=styles["BodyText"], fontSize=8, leading=10)

    doc = SimpleDocTemplate(filepath, pagesize=A4)
    elements = []

    elements.append(Paragraph("Rapport Global — OASIS AI Copilot (Linux)", title_style))
    elements.append(Paragraph(f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", body_style))
    elements.append(Spacer(1, 0.5 * cm))

    # Section KPIs
    elements.append(Paragraph("Indicateurs globaux", heading_style))
    kpi_table_data = [
        ["Indicateur", "Valeur"],
        ["Total incidents", str(kpis["total_incidents"])],
        ["Incidents ouverts", str(kpis["open_incidents"])],
        ["Incidents résolus", str(kpis["resolved_incidents"])],
        ["Temps moyen de résolution", f"{kpis['avg_resolution_minutes']} min" if kpis["avg_resolution_minutes"] else "N/A"],
    ]
    kpi_table = Table(kpi_table_data, colWidths=[8 * cm, 6 * cm])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 0.3 * cm))

    elements.append(Paragraph(
        f"<b>Répartition par catégorie :</b> "
        f"{', '.join(f'{k}: {v}' for k, v in kpis['incidents_by_category'].items()) or 'N/A'}",
        body_style,
    ))
    elements.append(Paragraph(
        f"<b>Répartition par sévérité :</b> "
        f"{', '.join(f'{k}: {v}' for k, v in kpis['incidents_by_severity'].items()) or 'N/A'}",
        body_style,
    ))

    # Section incidents ouverts
    elements.append(Paragraph(f"Incidents ouverts ({len(open_incidents)})", heading_style))
    elements.append(_build_incidents_table(open_incidents, small_style))

    # Section incidents résolus
    elements.append(Paragraph(f"Incidents résolus ({len(resolved_incidents)})", heading_style))
    elements.append(_build_incidents_table(resolved_incidents, small_style, show_resolved=True))

    doc.build(elements)
    return filepath


def _build_incidents_table(incidents: list, cell_style, show_resolved: bool = False):
    if not incidents:
        return Paragraph("Aucun incident dans cette catégorie.", cell_style)

    headers = ["ID", "Catégorie", "Sévérité", "Description", "Créé le"]
    if show_resolved:
        headers.append("Résolu le")

    data = [headers]
    for i in incidents:
        description = (i.response[:70] + "...") if len(i.response) > 70 else i.response
        row = [
            str(i.id),
            i.category or "N/A",
            i.severity or "N/A",
            Paragraph(description, cell_style),
            i.created_at.strftime("%d/%m %H:%M"),
        ]
        if show_resolved:
            row.append(i.resolved_at.strftime("%d/%m %H:%M") if i.resolved_at else "N/A")
        data.append(row)

    col_widths = [1.2 * cm, 2.2 * cm, 1.8 * cm, 7 * cm, 2.3 * cm]
    if show_resolved:
        col_widths.append(2.3 * cm)

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34495e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table
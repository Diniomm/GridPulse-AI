"""Downloadable report formats for the dashboard."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path


def report_to_pdf(report: dict[str, object], *, title: str, image_path: str | None = None) -> bytes:
    """Render a report as PDF using the optional reportlab dependency."""

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer
    except ImportError as error:
        raise RuntimeError("Install the export extra to generate PDF files.") from error

    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=letter, rightMargin=0.6 * inch, leftMargin=0.6 * inch)
    styles = getSampleStyleSheet()
    story = [Paragraph(title, styles["Title"]), Spacer(1, 0.15 * inch)]
    story.append(Paragraph(f"Status: {report.get('status', 'unknown')}", styles["Heading2"]))
    story.append(Paragraph(str(report.get("recommendation", "")), styles["BodyText"]))
    if image_path and Path(image_path).exists():
        story.extend([Spacer(1, 0.15 * inch), Image(image_path, width=5.8 * inch, height=3.6 * inch)])
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("Observations", styles["Heading2"]))
    for item in report.get("observations", []):
        story.append(Paragraph(f"{item.get('type', 'Observation')}: {item.get('value', '')}", styles["BodyText"]))
    story.append(Paragraph("Evidence and citations", styles["Heading2"]))
    for item in report.get("evidence", []):
        page = f", page {item.get('source_page')}" if item.get("source_page") else ""
        story.append(Paragraph(f"{item.get('title', 'Evidence')}{page} - {item.get('source_uri', '')}", styles["BodyText"]))
    story.append(Paragraph("Cause hypotheses", styles["Heading2"]))
    for item in report.get("hypotheses", []):
        story.append(Paragraph(f"{item.get('cause', 'Unresolved')} ({item.get('confidence', 0):.0%})", styles["BodyText"]))
        story.append(Paragraph(str(item.get("rationale", "")), styles["BodyText"]))
    document.build(story)
    return output.getvalue()

# =============================================================================
# crsc_calls — services/fir_pdf.py
# Builds a one-page FIR (Field Incident Report) summary PDF for a call that
# has reached one of the FIR_CLOSURE_STATUSES (FIR-Repair / FIR-Replace /
# FIR-Replace_Repair) — attached to the e-mail sent to the location that
# will handle the device (see services/email_utils.send_fir_pdf_email).
# =============================================================================
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

FIR_PDF_FIELDS = [
    ("Unique ID", "unique_id"),
    ("Call Status", "call_status"),
    ("VIN", "vin"),
    ("PSN", "psn"),
    ("Engineer Responsible", "complaint_assigned_to"),
    ("Device Model", "device_model"),
    ("Device IMEI", "device_IMEI"),
    ("Device ICCID", "device_ICCID"),
    ("Issue Identified", "issue_identified"),
    ("Engineer Recommendation", "engineer_recommendation"),
    ("Final Analysis", "final_analysis"),
    ("Device to be Sent", "device_to_be_sent"),
    ("Dealer Address", "dealer_address"),
    ("External Modification", "external_modification"),
]


def generate_fir_pdf(call):
    """Returns the PDF as raw bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()

    story = [
        Paragraph(f"FIR Summary — {call.unique_id}", styles["Title"]),
        Spacer(1, 8 * mm),
    ]

    rows = [[label, getattr(call, field, "") or ""] for label, field in FIR_PDF_FIELDS]
    table = Table(rows, colWidths=[55 * mm, 110 * mm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)

    doc.build(story)
    return buffer.getvalue()

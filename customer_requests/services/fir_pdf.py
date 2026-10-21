
import io
import os
from xml.sax.saxutils import escape

from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

FIR_PDF_FIELDS = [
    ("Service Request Number", "unique_id"),
    ("Date of Complaint", "date_of_complaint"),
    ("Complaint Raised By", "complaint_raised_by"),
    ("Contact Number", "contact_number"),
    ("Service Engineer Name", "complaint_assigned_to"),
    ("Device Model", "device_model"),
    ("PSN", "psn"),
    ("VIN Number", "vin"),
    ("Firmware Version", "exist_software"),
    ("Device ICCID", "device_ICCID"),
    ("Commercial Expiry Date", "activation_end_date"),
    ("Last communication in Darby", "last_communication_in_darby"),
    ("Vehicle Running Location", "vehicle_running_location"),
    ("Issue Identified", "issue_identified"),
    ("Issue_analysis", "issue_analysis"),
    ("External Modification", "external_modification"),
    ("Engineer Recommendation", "engineer_recommendation"),
    ("Device Sent To", "device_to_be_sent"),
    ("Dealer Address", "dealer_address"),
    ("Remarks", "remarks"),
]

FORMAT_REQ_NO = "ASS/011/08/21 Ver-2"
MANAGER_NAME = "Yogananda"
HEAD_NAME = "Narendra"  # falls back to the typed name if absent

LOGO_FILE = "company-logo.png"
HEAD_SIGNATURE_FILE = "SR SIGNATURE.png"  # falls back to the typed name if absent


def _fmt_date(value):
    if not value:
        return "N/A"
    if hasattr(value, "hour") and timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.strftime("%d-%m-%Y")


def _fmt_value(value):
    """Cell text for the details table - empty stays blank, datetimes are
    rendered as 'YYYY-MM-DD HH:MM:SS' in local time."""
    if value in (None, ""):
        return ""
    if hasattr(value, "hour"):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


def _image_or_none(filename, width, height):
    path = os.path.join(settings.BASE_DIR, "static", "images", filename)
    if os.path.exists(path):
        return Image(path, width, height)
    return None


def generate_fir_pdf(call):
    """Returns the PDF as raw bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    cell_style = ParagraphStyle("firCell", parent=getSampleStyleSheet()["Normal"], fontSize=9, leading=11)
    elements = []

    requested_date = _fmt_date(call.assigned_date or call.date_of_complaint)
    closure_date = _fmt_date(call.date_of_closure)
    engineer = call.complaint_assigned_to or "N/A"

    # ---- Header ----
    logo = _image_or_none(LOGO_FILE, 1.5 * inch, 0.5 * inch) or ""
    header_data = [
        [logo, "", "FIR", ""],
        ["Product Code", call.device_model or "N/A", "Centralised ID", call.unique_id or "N/A"],
        ["Customer", "A.L", "Format Req. No.", FORMAT_REQ_NO],
        ["Document by", "After Sales Support Team", "Date", requested_date],
    ]
    header_table = Table(header_data, colWidths=[1.5 * inch, 2 * inch, 2 * inch, 2 * inch])
    header_table.setStyle(TableStyle([
        ("SPAN", (0, 0), (1, 0)),
        ("SPAN", (2, 0), (3, 0)),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (2, 0), (3, 0), "Helvetica-Bold"),
        ("FONTSIZE", (2, 0), (3, 0), 16),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.2 * inch))

    # ---- Numbered details table ----
    table_data = [["SL No.", "Description", "Details"]]
    for i, (label, field) in enumerate(FIR_PDF_FIELDS, start=1):
        text = _fmt_value(getattr(call, field, ""))
        table_data.append([str(i), label, Paragraph(escape(text).replace("\n", "<br/>"), cell_style)])

    details_table = Table(table_data, colWidths=[0.5 * inch, 3.5 * inch, 3.5 * inch])
    details_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 0.2 * inch))

    # ---- Approval footer ----
    head_signature = _image_or_none(HEAD_SIGNATURE_FILE, 1.5 * inch, 0.5 * inch) or HEAD_NAME
    footer_data = [
        ["Approved By:", "Name", "Date", "Signature"],
        ["Service Engineer", engineer, requested_date, engineer],
        ["Manager", MANAGER_NAME, closure_date, MANAGER_NAME],
        ["Sales & Service Head", HEAD_NAME, closure_date, head_signature],
    ]
    footer_table = Table(footer_data, colWidths=[2 * inch, 2 * inch, 1.5 * inch, 2 * inch])
    footer_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 1, colors.black)]))
    elements.append(footer_table)

    doc.build(elements)
    return buffer.getvalue()

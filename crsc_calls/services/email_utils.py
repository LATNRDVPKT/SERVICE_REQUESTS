# =============================================================================
# crsc_calls — services/email_utils.py
# Standard Django SMTP e-mail, same pattern as AIS140_FLOW/services/email_utils.py.
# =============================================================================
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from crsc_calls.constants import CRSC_ASSIGNMENT_CC, CRSC_CUSTOMER_CC
from crsc_calls.services.fir_pdf import generate_fir_pdf

logger = logging.getLogger(__name__)


def _send(subject, template_name, context, to, cc=None, attachment=None, raw_attachments=None):
    """`attachment` is a Django FieldFile (e.g. call.upload_file). `raw_attachments`
    is an optional list of (filename, content_bytes, mimetype) tuples — for
    e.g. a generated PDF that never touches disk."""
    if not to:
        logger.warning("No recipient for e-mail '%s' — skipping send.", subject)
        return False

    html_body = render_to_string(template_name, context)
    message = EmailMultiAlternatives(
        subject=subject, body=html_body, from_email=settings.DEFAULT_FROM_EMAIL,
        to=to if isinstance(to, (list, tuple)) else [to], cc=cc or [],
    )
    message.attach_alternative(html_body, "text/html")

    if attachment:
        try:
            attachment.open()
            message.attach(attachment.name.split("/")[-1], attachment.read(), None)
        except Exception:  # noqa: BLE001
            logger.exception("Could not attach file to e-mail '%s'", subject)

    for filename, content, mimetype in (raw_attachments or []):
        message.attach(filename, content, mimetype)

    try:
        message.send(fail_silently=False)
        logger.info("E-mail SENT — subject=%r to=%s cc=%s", subject, message.to, message.cc)
        return True
    except Exception:  # noqa: BLE001
        logger.exception("E-mail FAILED — subject=%r to=%s cc=%s", subject, message.to, message.cc)
        return False


def send_assignment_email(call, part_b_url):
    if not call.submitted_to_email:
        return False
    return _send(
        subject=f"{call.unique_id} CRSC Assigned to {call.complaint_assigned_to} on {call.vin}",
        template_name="crsc_calls/emails/manager_email.html",
        context={"call": call, "part_b_url": part_b_url},
        to=[call.submitted_to_email], cc=CRSC_ASSIGNMENT_CC, attachment=call.upload_file,
    )


def send_customer_email(call):
    """Ticket-created notification — goes TO the customer, with the
    assigned engineer CC'd (not addressed directly) so the customer sees
    one clear "your ticket was created" e-mail."""
    recipients = [e.strip() for e in (call.customer_mail_id or "").split(";") if e.strip()]
    if not recipients or call.complaint_assigned_to == "--":
        return False
    cc = list(CRSC_CUSTOMER_CC)
    if call.submitted_to_email:
        cc.append(call.submitted_to_email)
    return _send(
        subject=f"Ticket Created: {call.unique_id} on Your Request",
        template_name="crsc_calls/emails/customer_email.html",
        context={"call": call},
        to=recipients, cc=cc,
    )


def send_fir_approval_email(call, recipients):
    if not recipients:
        return False
    return _send(
        subject=f"[CRSC] FIR Approval Requested — {call.unique_id}",
        template_name="crsc_calls/emails/fir_approval_email.html",
        context={"call": call},
        to=recipients,
    )


def send_remark_updated_email(call):
    """Sent to the assigned engineer every time a new follow-up round
    (Follow-Up Remark/Comment) is submitted, so they always have a record
    of what was just logged against their call."""
    if not call.submitted_to_email:
        return False
    return _send(
        subject=f"{call.unique_id} — Follow-Up Updated ({call.follow_up_level})",
        template_name="crsc_calls/emails/remark_updated_email.html",
        context={"call": call},
        to=[call.submitted_to_email], cc=CRSC_ASSIGNMENT_CC,
    )


def send_closure_email(call):
    """Sent to the customer (engineer CC'd) the first time a call reaches
    one of CUSTOMER_CLOSURE_STATUSES — same recipient shape as
    send_customer_email."""
    recipients = [e.strip() for e in (call.customer_mail_id or "").split(";") if e.strip()]
    if not recipients:
        return False
    cc = list(CRSC_CUSTOMER_CC)
    if call.submitted_to_email:
        cc.append(call.submitted_to_email)
    return _send(
        subject=f"{call.unique_id} — {call.call_status}",
        template_name="crsc_calls/emails/closure_email.html",
        context={"call": call},
        to=recipients, cc=cc,
    )


def send_fir_pdf_email(call, recipient):
    """Generates the FIR summary PDF and e-mails it to `recipient` — the
    address resolved from Device to be Sent via
    constants.resolve_fir_pdf_recipient()."""
    if not recipient:
        return False
    pdf_bytes = generate_fir_pdf(call)
    return _send(
        subject=f"FIR — {call.unique_id} ({call.call_status})",
        template_name="crsc_calls/emails/fir_pdf_email.html",
        context={"call": call},
        to=[recipient], cc=CRSC_ASSIGNMENT_CC,
        raw_attachments=[(f"FIR_{call.unique_id}.pdf", pdf_bytes, "application/pdf")],
    )

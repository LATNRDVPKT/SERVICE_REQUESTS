# =============================================================================
# crsc_calls — services/email_utils.py
# Standard Django SMTP e-mail, same pattern as AIS140_FLOW/services/email_utils.py.
# =============================================================================
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from crsc_calls.constants import CRSC_ASSIGNMENT_CC, CRSC_CUSTOMER_CC

logger = logging.getLogger(__name__)


def _send(subject, template_name, context, to, cc=None, attachment=None):
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

    try:
        message.send(fail_silently=False)
        return True
    except Exception:  # noqa: BLE001
        logger.exception("Failed to send e-mail '%s' to %s", subject, to)
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
    recipients = [e.strip() for e in (call.customer_mail_id or "").split(";") if e.strip()]
    if call.submitted_to_email:
        recipients.append(call.submitted_to_email)
    if not recipients or call.complaint_assigned_to == "--":
        return False
    return _send(
        subject=f"Ticket Created: {call.unique_id} on Your Request",
        template_name="crsc_calls/emails/customer_email.html",
        context={"call": call},
        to=recipients, cc=CRSC_CUSTOMER_CC,
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

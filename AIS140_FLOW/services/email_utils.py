# =============================================================================
# AIS140_FLOW — services/email_utils.py
# Standard Django SMTP e-mail (settings.EMAIL_* — see .env.example).
# Four triggers, matching Section 9 of the specification:
#   - Part-A assignment e-mail
#   - D1/D2 show-stopper e-mail
#   - Completion e-mail
#   - Remarks-updated e-mail (from the AL API)
# =============================================================================
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from AIS140_FLOW.constants import PART_A_ASSIGNMENT_CC, STATE_EXTRA_EMAILS

logger = logging.getLogger(__name__)


def _send(subject, template_name, context, to, cc=None, attachments=None):
    if not to:
        logger.warning("No recipient for e-mail '%s' — skipping send.", subject)
        return False

    html_body = render_to_string(template_name, context)
    message = EmailMultiAlternatives(
        subject=subject,
        body=html_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=to if isinstance(to, (list, tuple)) else [to],
        cc=cc or [],
    )
    message.attach_alternative(html_body, "text/html")

    for attachment in attachments or []:
        try:
            attachment.open()
            message.attach(attachment.name.split("/")[-1], attachment.read(), None)
        except Exception:  # noqa: BLE001 — never let an attachment error block the e-mail
            logger.exception("Could not attach file %s to e-mail '%s'", attachment, subject)

    try:
        message.send(fail_silently=False)
        logger.info("E-mail SENT — subject=%r to=%s cc=%s", subject, message.to, message.cc)
        return True
    except Exception:  # noqa: BLE001
        logger.exception("E-mail FAILED — subject=%r to=%s cc=%s", subject, message.to, message.cc)
        return False


def _extra_cc_for_state(state):
    return STATE_EXTRA_EMAILS.get((state or "").strip().upper(), [])


def send_part_a_assignment_email(ticket, part_b_url):
    if not ticket.assigned_engineer_email or ticket.assigned_engineer_email in ("--", ""):
        return False
    return _send(
        subject=f"[AIS140] Ticket {ticket.unique_id} assigned to you",
        template_name="AIS140_FLOW/emails/part_a_email.html",
        context={"ticket": ticket, "part_b_url": part_b_url},
        to=[ticket.assigned_engineer_email],
        cc=PART_A_ASSIGNMENT_CC,
    )


def send_request_remark_email(ticket, part_b_url):
    if not ticket.request_remarks:
        return False
    recipients = [e for e in [ticket.assigned_engineer_email, ticket.Dealer_mail] if e]
    return _send(
        subject=f"[AIS140] Request remark update on ticket {ticket.unique_id}",
        template_name="AIS140_FLOW/emails/request_remark_email.html",
        context={"ticket": ticket, "part_b_url": part_b_url},
        to=recipients,
        cc=_extra_cc_for_state(ticket.state),
    )


def send_completion_email(ticket):
    recipients = [e for e in [ticket.assigned_engineer_email, ticket.Dealer_mail, ticket.TSM_mail] if e]
    attachments = [f for f in [ticket.upload_certificate_in_ialert_01, ticket.upload_certificate_in_ialert] if f]
    return _send(
        subject=f"[AIS140] Ticket {ticket.unique_id} — {ticket.completion_status}",
        template_name="AIS140_FLOW/emails/completion_email.html",
        context={"ticket": ticket},
        to=recipients,
        cc=_extra_cc_for_state(ticket.state),
        attachments=attachments,
    )


def send_remarks_updated_email(ticket):
    recipients = [e for e in [ticket.assigned_engineer_email] if e]
    return _send(
        subject=f"[AIS140] AL updated remarks on ticket {ticket.unique_id}",
        template_name="AIS140_FLOW/emails/remarks_updated_email.html",
        context={"ticket": ticket},
        to=recipients,
    )

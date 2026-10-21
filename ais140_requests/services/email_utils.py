# =============================================================================
# ais140_requests — services/email_utils.py
# Standard Django SMTP e-mail (settings.EMAIL_* — see .env.example).
# Four triggers, matching Section 9 of the specification:
#   - manager-form assignment e-mail
#   - D1/D2 show-stopper e-mail
#   - Completion e-mail
#   - Remarks-updated e-mail (from the AL API)
# =============================================================================
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from ais140_requests.constants import (
    AIS140_FIXED_RECIPIENTS, COMPLETION_CC, COMPLETION_STATE_EXTRA_EMAILS,
    PART_A_ASSIGNMENT_CC, SHOW_STOPPER_CC, STATE_EXTRA_EMAILS,
)

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


def send_assignment_email(ticket, engineer_form_url):
    if not ticket.assigned_engineer_email or ticket.assigned_engineer_email in ("--", ""):
        return False
    return _send(
        subject=f"AIS140 Part-A Form Submission — {ticket.unique_id}",
        template_name="ais140_requests/emails/assignment_email.html",
        context={"ticket": ticket, "engineer_form_url": engineer_form_url},
        to=[ticket.assigned_engineer_email],
        cc=PART_A_ASSIGNMENT_CC,
    )


def _split_addresses(value):
    """One field may hold several addresses separated by ';' or ','."""
    out = []
    for part in str(value or "").replace(";", ",").split(","):
        part = part.strip()
        if part and part != "--":
            out.append(part)
    return out


def _unique(addresses):
    seen, out = set(), []
    for a in addresses:
        key = a.lower()
        if key not in seen:
            seen.add(key)
            out.append(a)
    return out


def _follow_ups(ticket):
    """The ticket's numbered request-remark pushes (D1, D2, ... Dn), oldest
    first — the latest event for each number."""
    latest = {}
    rows = ticket.history.filter(source_field="request_remarks").exclude(follow_up__isnull=True) \
        .exclude(follow_up="").order_by("remark_datetime", "created_at")
    for row in rows:
        latest[row.follow_up] = row

    def _n(row):
        try:
            return int(row.follow_up[1:])
        except ValueError:
            return 0

    return sorted(latest.values(), key=_n)


def _stakeholder_recipients(ticket):
    recipients = (
        _split_addresses(ticket.assigned_engineer_email)
        + _split_addresses(ticket.Customer_Email_ID)
        + _split_addresses(ticket.Dealer_mail)
        + _split_addresses(ticket.additional_email_id)
        + _split_addresses(ticket.TSM_mail)
        + list(AIS140_FIXED_RECIPIENTS)
    )
    return recipients


def send_show_stopper_email(ticket):
    """Sent when an engineer pushes a request remark (D1, D2, ... Dn).
    Subject: "AIS140 Certificate Generation - Show Stopper <ID> on <VIN>"."""
    recipients = _unique(_stakeholder_recipients(ticket) + STATE_EXTRA_EMAILS.get(ticket.state, []))
    return _send(
        subject=f"AIS140 Certificate Generation - Show Stopper {ticket.unique_id} on {ticket.vin_no}",
        template_name="ais140_requests/emails/request_remark_email.html",
        context={"ticket": ticket, "follow_ups": _follow_ups(ticket)},
        to=recipients,
        cc=list(SHOW_STOPPER_CC),
    )


def send_completion_email(ticket):
    """Sent when a certificate is uploaded (or the ticket reaches a terminal
    completion status), with the uploaded certificates attached.
    Subject: "AIS140 Request Completed : <ID>"."""
    extra = COMPLETION_STATE_EXTRA_EMAILS.get((ticket.state or "").strip().upper(), [])
    recipients = _unique(_stakeholder_recipients(ticket) + extra)
    attachments = [
        f for f in (
            ticket.upload_certificate_in_ialert,
            ticket.upload_certificate_in_ialert_01,
            ticket.upload_certificate_in_ialert_02,
        ) if f
    ]
    return _send(
        subject=f"AIS140 Request Completed : {ticket.unique_id}",
        template_name="ais140_requests/emails/completion_email.html",
        context={"ticket": ticket, "follow_ups": _follow_ups(ticket)},
        to=recipients,
        cc=list(COMPLETION_CC),
        attachments=attachments,
    )


def send_remarks_updated_email(ticket, engineer_form_url=None):
    recipients = [e for e in [ticket.assigned_engineer_email] if e]
    return _send(
        subject=f"AIS140 Remarks Updated — {ticket.unique_id}",
        template_name="ais140_requests/emails/remarks_updated_email.html",
        context={"ticket": ticket, "engineer_form_url": engineer_form_url},
        to=recipients,
    )

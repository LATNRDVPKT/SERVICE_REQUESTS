# =============================================================================
# AIS140_FLOW — services/latest_update.py
# REQ-07 — for a given ticket, work out the single most recent event and its
# remark/comments/timestamp/responsibility, by comparing every tracked
# field's own timestamp (REQ-06) and taking the maximum.
# =============================================================================
from AIS140_FLOW.constants import get_responsibility, CERTIFICATE_EVENT_REMARKS


def get_latest_ticket_update(ticket):
    """
    Returns:
        {"remark": str, "comments": str, "updated_at": datetime | None,
         "source": str, "responsibility": str}
    or all-blank values if the ticket has no tracked events yet.
    """
    candidates = []

    if ticket.upload_certificate_in_ialert_01 and ticket.permanent_cert_date:
        candidates.append((
            ticket.permanent_cert_date,
            CERTIFICATE_EVENT_REMARKS["permanent_certificate"], "",
            "permanent_certificate",
        ))
    if ticket.upload_certificate_in_ialert and ticket.temp_cert_date:
        candidates.append((
            ticket.temp_cert_date,
            CERTIFICATE_EVENT_REMARKS["temporary_certificate"], "",
            "temporary_certificate",
        ))
    if ticket.request_remarks and (ticket.request_remarks_updated_at or ticket.request_closure):
        candidates.append((
            ticket.request_remarks_updated_at or ticket.request_closure,
            ticket.request_remarks, ticket.request_comments or "",
            "request_remarks",
        ))
    if ticket.AL_remarks and ticket.al_remarks_updated_at:
        candidates.append((
            ticket.al_remarks_updated_at, ticket.AL_remarks, ticket.AL_comments or "",
            "al_remarks",
        ))
    if ticket.reupdated_request_al and ticket.reupdated_request_al_updated_at:
        candidates.append((
            ticket.reupdated_request_al_updated_at,
            str(ticket.reupdated_request_al), "",
            "reupdated_request_al",
        ))

    if not candidates:
        return {"remark": "", "comments": "", "updated_at": None, "source": "", "responsibility": ""}

    latest_dt, latest_remark, latest_comments, source = max(candidates, key=lambda c: c[0])
    return {
        "remark": latest_remark,
        "comments": latest_comments,
        "updated_at": latest_dt,
        "source": source,
        "responsibility": get_responsibility(latest_remark),
    }

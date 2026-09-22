# =============================================================================
# AIS140_FLOW — services/workflow.py
# All the Part-B "on save" business rules live here so views.py stays thin:
#   REQ-02  Automatic request closure timestamp
#   REQ-04  Automatic Update_to_AL_API determination
#   REQ-05  Automatic certificate date/time stamps
#   REQ-06  Per-field update timestamps
#   REQ-09  Update-history row creation (now includes attending_engineer)
# =============================================================================
from django.utils.timezone import now

from AIS140_FLOW.constants import get_responsibility, CERTIFICATE_EVENT_REMARKS, REMARK_COMMENT_MAP
from AIS140_FLOW.models import AIS140RequestUpdate


def _blank(value):
    return value is None or (isinstance(value, str) and not value.strip())


def determine_update_to_al_api(instance):
    """
    REQ-04 — priority order: Permanent -> Temporary -> Request -> None.
    (Collapsed from the earlier Permanent -> Temporary -> D2 -> D1 chain
    now that D1/D2 have been merged into one request-remarks field.)
    """
    permanent_file = bool(instance.upload_certificate_in_ialert_01)
    temporary_file = bool(instance.upload_certificate_in_ialert)

    if permanent_file and temporary_file:
        return "Temp + Perm"
    if permanent_file:
        return "Permanent"
    if temporary_file:
        return "Temporary"
    if not _blank(instance.request_remarks):
        return "Request"
    return ""  # priority 4 — "No update"


def apply_part_b_business_rules(instance, previous):
    """
    Mutates `instance` in place to apply REQ-02, REQ-03, REQ-05 and REQ-06,
    then returns the list of AIS140RequestUpdate rows that should be created
    for this save (REQ-09), which the caller writes *after* instance.save()
    succeeds so the history table always matches what was actually
    persisted.

    `previous` is the ticket's state *before* this save (None for a brand
    new ticket).
    """
    timestamp = now()
    history_rows = []

    prev_request_remarks = (previous.request_remarks if previous else "") or ""
    prev_al_remarks = (previous.AL_remarks if previous else "") or ""
    prev_reupdated = previous.reupdated_request_al if previous else None
    prev_temp_cert_name = previous.upload_certificate_in_ialert.name if previous and previous.upload_certificate_in_ialert else ""
    prev_perm_cert_name = previous.upload_certificate_in_ialert_01.name if previous and previous.upload_certificate_in_ialert_01 else ""

    # ------------------------------------------------------------------
    # Request Remarks / Comments never lock — every actual change is
    # recorded as a new history row and refreshes request_remarks_updated_at.
    # request_closure is stamped the first time a remark is submitted and
    # left as-is afterwards (it marks when the ticket was first worked).
    # ------------------------------------------------------------------
    if not _blank(instance.request_remarks) and _blank(instance.request_comments):
        instance.request_comments = REMARK_COMMENT_MAP.get(
            str(instance.request_remarks).strip().upper(), instance.request_comments
        )

    remarks_changed = (instance.request_remarks or "") != prev_request_remarks
    comments_changed = (instance.request_comments or "") != ((previous.request_comments if previous else "") or "")
    if not _blank(instance.request_remarks) and (remarks_changed or comments_changed):
        if _blank(prev_request_remarks):
            instance.request_closure = timestamp
        instance.request_remarks_updated_at = timestamp
        history_rows.append(dict(
            source_field="request_remarks", latest_remark=instance.request_remarks,
            latest_comments=instance.request_comments, remark_datetime=timestamp,
            attending_engineer=instance.attending_engineer,
        ))

    # ------------------------------------------------------------------
    # AL remarks change -> timestamp + history row
    # ------------------------------------------------------------------
    if not _blank(instance.AL_remarks) and instance.AL_remarks != prev_al_remarks:
        instance.al_remarks_updated_at = timestamp
        history_rows.append(dict(
            source_field="al_remarks", latest_remark=instance.AL_remarks,
            latest_comments=instance.AL_comments, remark_datetime=timestamp,
            attending_engineer=instance.attending_engineer,
        ))

    # ------------------------------------------------------------------
    # Reupdated-to-AL change -> timestamp + history row
    # ------------------------------------------------------------------
    if instance.reupdated_request_al and instance.reupdated_request_al != prev_reupdated:
        instance.reupdated_request_al_updated_at = timestamp
        history_rows.append(dict(
            source_field="reupdated_request_al", latest_remark=str(instance.reupdated_request_al),
            latest_comments="", remark_datetime=timestamp,
            attending_engineer=instance.attending_engineer,
        ))

    # ------------------------------------------------------------------
    # REQ-05 — certificate dates, only when the file actually changed
    # ------------------------------------------------------------------
    new_temp_name = instance.upload_certificate_in_ialert.name if instance.upload_certificate_in_ialert else ""
    if new_temp_name and new_temp_name != prev_temp_cert_name:
        instance.temp_cert_date = timestamp
        instance.temp_cert_updated_at = timestamp
        history_rows.append(dict(
            source_field="temporary_certificate",
            latest_remark=CERTIFICATE_EVENT_REMARKS["temporary_certificate"],
            latest_comments="", remark_datetime=timestamp,
            attending_engineer=instance.attending_engineer,
        ))

    new_perm_name = instance.upload_certificate_in_ialert_01.name if instance.upload_certificate_in_ialert_01 else ""
    if new_perm_name and new_perm_name != prev_perm_cert_name:
        instance.permanent_cert_date = timestamp
        instance.permanent_cert_updated_at = timestamp
        history_rows.append(dict(
            source_field="permanent_certificate",
            latest_remark=CERTIFICATE_EVENT_REMARKS["permanent_certificate"],
            latest_comments="", remark_datetime=timestamp,
            attending_engineer=instance.attending_engineer,
        ))

    # ------------------------------------------------------------------
    # REQ-04 — Update_to_AL_API, always recomputed server-side
    # ------------------------------------------------------------------
    instance.Update_to_AL_API = determine_update_to_al_api(instance)

    # ------------------------------------------------------------------
    # REQ-08 — responsibility, set from whichever event ends up latest
    # once history rows are known
    # ------------------------------------------------------------------
    if history_rows:
        latest_event = max(history_rows, key=lambda r: r["remark_datetime"])
        instance.responsibility = get_responsibility(latest_event["source_field"], latest_event["latest_remark"])

    # A cancelled request's responsibility is always Customer, regardless of
    # which remark/event was most recently logged.
    if instance.completion_status == "Cancelled":
        instance.responsibility = "CUSTOMER"

    return history_rows


def write_history_rows(ticket, history_rows):
    """Persist the AIS140RequestUpdate rows computed by apply_part_b_business_rules."""
    objs = []
    for row in history_rows:
        objs.append(AIS140RequestUpdate(
            ticket=ticket,
            unique_id=ticket.unique_id,
            vin_no=ticket.vin_no,
            latest_remark=row["latest_remark"],
            latest_comments=row.get("latest_comments", ""),
            remark_datetime=row["remark_datetime"],
            responsibility=get_responsibility(row["source_field"], row["latest_remark"]),
            attending_engineer=row.get("attending_engineer") or ticket.attending_engineer,
            source_field=row["source_field"],
        ))
    if objs:
        AIS140RequestUpdate.objects.bulk_create(objs)

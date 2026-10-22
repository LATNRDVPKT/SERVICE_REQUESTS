# =============================================================================
# ais140_requests — services/workflow.py
# All the engineer-form "on save" business rules live here so views.py stays thin:
#   REQ-02  Automatic request closure timestamp
#   REQ-04  Automatic Update_to_AL_API (from what this save uploaded)
#   REQ-05  Automatic certificate date/time stamps + "raised by" engineer
#           + completion date = latest certificate date
#   REQ-06  Per-field update timestamps
#   REQ-09  Update-history row creation (now includes attending_engineer)
# =============================================================================
from django.utils.timezone import now

from ais140_requests.constants import get_responsibility, CERTIFICATE_EVENT_REMARKS, REMARK_COMMENT_MAP
from ais140_requests.models import AIS140RequestUpdate

def _blank(value):
    return value is None or (isinstance(value, str) and not value.strip())

def _file_name(file_field):
    return file_field.name if file_field else ""


def update_to_al_api_for_this_save(new_permanent_upload, new_temporary_upload):
    """
    REQ-04 — what this save sends to AL, decided automatically (the engineer
    no longer picks it): a newly uploaded Permanent/Vahan certificate wins,
    then a newly uploaded Temporary certificate, otherwise it's a Remark.
    """
    if new_permanent_upload:
        return "Permanent"
    if new_temporary_upload:
        return "Temporary"
    return "Remark"


def latest_certificate_date(ticket):
    """Completion Date = the later of the Temporary / Permanent certificate dates."""
    certificate_dates = [d for d in (ticket.temp_cert_date, ticket.permanent_cert_date) if d]
    return max(certificate_dates) if certificate_dates else None

def apply_engineer_form_rules(instance, previous):
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
    prev_vahan_cert_name = _file_name(previous.upload_certificate_in_ialert_02) if previous else ""

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
    # REQ-05 — certificate dates and "raised by", only when the file
    # actually changed. "Raised by" is the logged-in engineer (the view
    # stamps attending_engineer from request.user before calling this).
    # ------------------------------------------------------------------
    new_temp_name = instance.upload_certificate_in_ialert.name if instance.upload_certificate_in_ialert else ""
    temporary_uploaded_now = bool(new_temp_name) and new_temp_name != prev_temp_cert_name
    if temporary_uploaded_now:
        instance.temp_cert_date = timestamp
        instance.temp_cert_updated_at = timestamp
        instance.temp_raised_by = instance.attending_engineer
        history_rows.append(dict(
            source_field="temporary_certificate",
            latest_remark=CERTIFICATE_EVENT_REMARKS["temporary_certificate"],
            latest_comments="", remark_datetime=timestamp,
            attending_engineer=instance.attending_engineer,
        ))

    new_perm_name = instance.upload_certificate_in_ialert_01.name if instance.upload_certificate_in_ialert_01 else ""
    permanent_uploaded_now = bool(new_perm_name) and new_perm_name != prev_perm_cert_name
    if permanent_uploaded_now:
        instance.permanent_cert_date = timestamp
        instance.permanent_cert_updated_at = timestamp
        instance.perm_raised_by = instance.attending_engineer
        history_rows.append(dict(
            source_field="permanent_certificate",
            latest_remark=CERTIFICATE_EVENT_REMARKS["permanent_certificate"],
            latest_comments="", remark_datetime=timestamp,
            attending_engineer=instance.attending_engineer,
        ))

    new_vahan_name = _file_name(instance.upload_certificate_in_ialert_02)
    vahan_uploaded_now = bool(new_vahan_name) and new_vahan_name != prev_vahan_cert_name

    instance.Update_to_AL_API = update_to_al_api_for_this_save(
        new_permanent_upload=permanent_uploaded_now or vahan_uploaded_now,
        new_temporary_upload=temporary_uploaded_now,
    )

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
    """Persist the AIS140RequestUpdate rows computed by apply_engineer_form_rules."""
    objs = []
    # Each request-remark push becomes the next follow-up: D1, D2, D3 ... Dn.
    follow_up_count = ticket.history.filter(source_field="request_remarks").count()
    for row in history_rows:
        follow_up = ""
        if row["source_field"] == "request_remarks":
            follow_up_count += 1
            follow_up = f"D{follow_up_count}"
        objs.append(AIS140RequestUpdate(
            follow_up=follow_up,
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

# =============================================================================
# crsc_calls — services/workflow.py
# Save-time business rules for Part-B:
#   - Follow-Up Remark/Comment never lock — every actual change (in either
#     field) is a new follow-up round: advances D1 -> D2 -> D3, re-schedules
#     next_follow_up_exp_date for iAlert calls, stamps follow_up_closure_date,
#     refreshes follow_up_updated_at, and is recorded as a new history row.
#     Same "never lock, track every real change" convention as AIS140's
#     request_remarks/request_comments.
#   - write DirectCallUpdate history rows
# =============================================================================
from datetime import timedelta

from django.utils.timezone import now

from crsc_calls.constants import get_responsibility, format_update_to_al
from crsc_calls.models import DirectCallUpdate
from crsc_calls.services.latest_update import get_latest_call_update

D2_DELAY_DAYS = 2
D3_DELAY_DAYS = 3


def _blank(value):
    return value is None or (isinstance(value, str) and not value.strip())


def _next_follow_up_level(previous_level):
    """D1 -> D2 -> D3, then stays at D3 forever — once a call has reached
    D3, any further follow-up round is still recorded (new history row,
    refreshed follow_up_updated_at) but never advances past D3 or wraps
    back to D1."""
    if previous_level == "D1":
        return "D2"
    if previous_level in ("D2", "D3"):
        return "D3"
    return "D1"


def apply_follow_up_rules(instance, previous):
    """
    Mutates `instance` in place. Returns the list of DirectCallUpdate rows
    to write after save (same append-after-commit pattern as AIS140).
    """
    timestamp = now()
    history_rows = []

    # Date of Closure was a manually-typed field that engineers kept
    # forgetting to fill in, leaving Overall TAT permanently blank —
    # auto-stamp it the first time a call leaves Pending (any other
    # call_status), same convention as AIS140's completion_date auto-stamp.
    # Left untouched once set, and never touched while still Pending.
    if (instance.call_status or "Pending") != "Pending" and not instance.date_of_closure:
        instance.date_of_closure = timestamp

    prev_remark = (previous.follow_up_remark if previous else "") or ""
    prev_comment = (previous.follow_up_comment if previous else "") or ""
    prev_al_contact = (previous.al_updated_contact_no if previous else "") or ""

    remark_changed = (instance.follow_up_remark or "") != prev_remark
    comment_changed = (instance.follow_up_comment or "") != prev_comment
    if not _blank(instance.follow_up_remark) and (remark_changed or comment_changed):
        # A new follow-up round — either the very first one, or an engineer
        # (or admin) following up again after an earlier round.
        previous_level = previous.follow_up_level if previous else None
        instance.follow_up_level = _next_follow_up_level(previous_level)
        instance.follow_up_closure_date = timestamp
        instance.follow_up_updated_at = timestamp

        if instance.call_type == "ialert_call":
            if instance.follow_up_level == "D1":
                instance.next_follow_up_exp_date = timestamp + timedelta(days=D2_DELAY_DAYS)
            elif instance.follow_up_level == "D2":
                instance.next_follow_up_exp_date = timestamp + timedelta(days=D3_DELAY_DAYS)
            else:
                instance.next_follow_up_exp_date = None

        history_rows.append(dict(
            source_field="follow_up", follow_up_level=instance.follow_up_level,
            remark=instance.follow_up_remark, comment=instance.follow_up_comment,
            event_datetime=timestamp, next_follow_up_exp_date=instance.next_follow_up_exp_date,
            engineer=instance.follow_up_engineer,
        ))

    # AL-updated contact number — its own tracked event
    if not _blank(instance.al_updated_contact_no) and instance.al_updated_contact_no != prev_al_contact:
        instance.al_updated_contact_no_updated_at = timestamp
        history_rows.append(dict(
            source_field="al_updated_contact_no", follow_up_level=instance.follow_up_level,
            remark="", comment="", al_updated_contact_no=instance.al_updated_contact_no,
            event_datetime=timestamp, engineer=instance.follow_up_engineer,
        ))

    # Keep the stored Responsibility in sync with whichever event (follow-up
    # remark vs. AL Updated Contact No) is now the most recent.
    instance.responsibility = get_latest_call_update(instance)["responsibility"]

    return history_rows


def write_history_rows(call, history_rows):
    objs = []
    for row in history_rows:
        objs.append(DirectCallUpdate(
            call=call,
            unique_id=call.unique_id,
            vin_no=call.vin,
            follow_up_level=row.get("follow_up_level"),
            remark=row.get("remark", ""),
            comment=row.get("comment", ""),
            event_datetime=row["event_datetime"],
            next_follow_up_exp_date=row.get("next_follow_up_exp_date"),
            al_updated_contact_no=row.get("al_updated_contact_no", ""),
            responsibility=get_responsibility(row["source_field"], row.get("remark")),
            engineer=row.get("engineer", ""),
            source_field=row["source_field"],
        ))
    if objs:
        DirectCallUpdate.objects.bulk_create(objs)


def build_update_to_al(call):
    """'D1 - iALERT ISSUE' style string, ready to push to the AL API."""
    return format_update_to_al(call.follow_up_level, call.follow_up_remark)

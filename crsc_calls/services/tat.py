# =============================================================================
# crsc_calls — services/tat.py
# Turn-around-time calculations shown on the real-time dashboard:
#   D0 TAT column (d1_tat)     = Assigned Date          - Date of Complaint
#   D1 TAT column (d2_tat)     = First Follow-Up Update - Assigned Date
#   Overall TAT column (total_tat) = Date of Closure    - Assigned Date
# Each is only (re)computed once both of its inputs are available, and is
# left untouched otherwise so an earlier value never gets silently blanked.
# =============================================================================


def _format_duration(delta):
    """HH:MM:SS — hours are not capped at 24, so a multi-day gap still reads
    as one running hour count (e.g. 30:15:00 for 1 day 6h 15m)."""
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        total_seconds = 0
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def compute_tats(call):
    """Mutates `call` in place, recomputing d1_tat / d2_tat / total_tat."""
    if call.assigned_date and call.date_of_complaint:
        call.d1_tat = _format_duration(call.assigned_date - call.date_of_complaint)
    if call.assigned_date and call.follow_up_updated_at:
        call.d2_tat = _format_duration(call.follow_up_updated_at - call.assigned_date)
    if call.assigned_date and call.date_of_closure:
        call.total_tat = _format_duration(call.date_of_closure - call.assigned_date)

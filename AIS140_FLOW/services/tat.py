# =============================================================================
# AIS140_FLOW — services/tat.py
# Turn-around-time calculations shown on the real-time dashboard, same
# HH:MM:SS convention as crsc_calls.services.tat:
#   D1 TAT column (D1_TAT)   = Assigned to Engineer Date - AL Assigned Date
#   Overall TAT column (total_tat) = Completion Date     - Assigned to Engineer Date
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


def compute_tats(ticket):
    """Mutates `ticket` in place, recomputing D1_TAT / total_tat."""
    if ticket.Customer_assigned_date and ticket.date_of_request:
        ticket.D1_TAT = _format_duration(ticket.Customer_assigned_date - ticket.date_of_request)
    if ticket.completion_date and ticket.Customer_assigned_date:
        ticket.total_tat = _format_duration(ticket.completion_date - ticket.Customer_assigned_date)

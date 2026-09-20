# =============================================================================
# AIS140_FLOW — services/dashboard_stats.py
# Chart/card data for the Real-Time dashboard. All of this is computed from
# whatever queryset the dashboard is currently showing, so the charts move
# together with the live filters.
#
# "Completed" is defined per-state, as specified:
#   - Karnataka, Tamil Nadu, Himachal Pradesh -> completion_status == "Temporary"
#   - every other state                        -> completion_status == "Permanent"
# =============================================================================
from django.db.models import Case, When, Value, BooleanField, Count, Q

STATES_USING_TEMPORARY_AS_COMPLETE = {"KARNATAKA", "TAMIL NADU", "HIMACHAL PRADESH"}


def _completed_q():
    """A Q object matching 'completed' per the state-dependent rule above."""
    special = Q(state__iexact="KARNATAKA") | Q(state__iexact="TAMIL NADU") | Q(state__iexact="HIMACHAL PRADESH")
    return (special & Q(completion_status="Temporary")) | (~special & Q(completion_status="Permanent"))


def build_dashboard_stats(queryset):
    """
    Returns a JSON-serialisable dict:
        {
          "received_count": int,
          "completed_count": int,
          "state_bar": {"labels": [...], "received": [...], "completed": [...]},
          "engineer_pie": {"labels": [...], "values": [...]},
        }
    """
    completed_q = _completed_q()

    received_count = queryset.count()
    completed_count = queryset.filter(completed_q).count()

    # State-wise received vs completed
    state_rows = (
        queryset.exclude(state__isnull=True).exclude(state__exact="")
        .values("state")
        .annotate(
            received=Count("id"),
            completed=Count("id", filter=completed_q),
        )
        .order_by("-received")[:15]
    )
    state_bar = {
        "labels": [row["state"] for row in state_rows],
        "received": [row["received"] for row in state_rows],
        "completed": [row["completed"] for row in state_rows],
    }

    # Engineer-wise completed-ticket counts
    engineer_rows = (
        queryset.filter(completed_q)
        .exclude(assigned_engineer_email__isnull=True)
        .exclude(assigned_engineer_email__in=["", "--"])
        .values("assigned_engineer_email")
        .annotate(completed=Count("id"))
        .order_by("-completed")[:12]
    )
    engineer_pie = {
        "labels": [row["assigned_engineer_email"] for row in engineer_rows],
        "values": [row["completed"] for row in engineer_rows],
    }

    return {
        "received_count": received_count,
        "completed_count": completed_count,
        "state_bar": state_bar,
        "engineer_pie": engineer_pie,
    }

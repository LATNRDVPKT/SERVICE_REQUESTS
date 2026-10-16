# =============================================================================
# crsc_calls — services/dashboard_stats.py
# Cards + charts for the Real-Time dashboard, computed from whatever
# queryset is currently on screen (same "moves with the filters" approach
# as AIS140).
# =============================================================================
from django.db.models import Count, Q

CLOSED_STATUSES = ["Closed", "Closed-CI", "Resolved", "Auto-Resolved"]

# call_type is stored two ways: the form saves the display label ("iAlert
# Call") while the iAlert API saves a snake_case key ("ialert_call"). Match both.
CALL_TYPE_VALUES = {
    "ialert_call": ["iAlert Call", "ialert_call"],
    "direct_call": ["Direct Call", "direct_call"],
    "plant_call": ["Plant Call", "plant_call"],
}


def call_type_values(call_type):
    """All stored spellings for a call_type key; unknown values match as-is."""
    return CALL_TYPE_VALUES.get(call_type, [call_type])


def _status_breakdown(queryset, call_type):
    """Call-status counts for one call_type — feeds the per-type bar chart."""
    rows = (
        queryset.filter(call_type__in=call_type_values(call_type))
        .exclude(call_status__isnull=True).exclude(call_status__exact="")
        .values("call_status").annotate(count=Count("id")).order_by("-count")
    )
    return {
        "labels": [row["call_status"] for row in rows],
        "values": [row["count"] for row in rows],
    }


def build_dashboard_stats(queryset):
    closed_q = Q(call_status__in=CLOSED_STATUSES)

    ialert_qs = queryset.filter(call_type__in=call_type_values("ialert_call"))
    direct_qs = queryset.filter(call_type__in=call_type_values("direct_call"))
    plant_qs = queryset.filter(call_type__in=call_type_values("plant_call"))

    return {
        "total_calls": queryset.count(),
        "ialert_received": ialert_qs.count(),
        "ialert_completed": ialert_qs.filter(closed_q).count(),
        "direct_received": direct_qs.count(),
        "direct_completed": direct_qs.filter(closed_q).count(),
        "plant_received": plant_qs.count(),
        "plant_completed": plant_qs.filter(closed_q).count(),
        "ialert_status": _status_breakdown(queryset, "ialert_call"),
        "direct_status": _status_breakdown(queryset, "direct_call"),
        "plant_status": _status_breakdown(queryset, "plant_call"),
    }

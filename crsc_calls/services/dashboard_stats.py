# =============================================================================
# crsc_calls — services/dashboard_stats.py
# Cards + charts for the Real-Time dashboard, computed from whatever
# queryset is currently on screen (same "moves with the filters" approach
# as AIS140).
# =============================================================================
from django.db.models import Count, Q


def build_dashboard_stats(queryset):
    received_count = queryset.count()
    closed_q = Q(call_status__in=["Closed", "Closed-CI", "Resolved", "Auto-Resolved"])
    closed_count = queryset.filter(closed_q).count()
    pending_count = received_count - closed_count

    status_rows = (
        queryset.exclude(call_status__isnull=True).exclude(call_status__exact="")
        .values("call_status").annotate(count=Count("id")).order_by("-count")
    )
    status_bar = {
        "labels": [row["call_status"] for row in status_rows],
        "values": [row["count"] for row in status_rows],
    }

    engineer_rows = (
        queryset.exclude(complaint_assigned_to__isnull=True).exclude(complaint_assigned_to__exact="")
        .values("complaint_assigned_to").annotate(count=Count("id")).order_by("-count")[:12]
    )
    engineer_pie = {
        "labels": [row["complaint_assigned_to"] for row in engineer_rows],
        "values": [row["count"] for row in engineer_rows],
    }

    return {
        "received_count": received_count,
        "closed_count": closed_count,
        "pending_count": pending_count,
        "status_bar": status_bar,
        "engineer_pie": engineer_pie,
    }

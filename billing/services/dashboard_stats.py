# =============================================================================
# billing — services/dashboard_stats.py
# Chart data for the Real-Time dashboard, computed from whatever queryset
# is currently on screen — same "moves with the filters" approach as
# AIS140/crsc_calls's dashboard stats.
# =============================================================================
from django.db.models import Sum


def _breakdown(queryset, group_field, value_field):
    rows = (
        queryset.exclude(**{f"{group_field}__isnull": True}).exclude(**{f"{group_field}__exact": ""})
        .values(group_field).annotate(total=Sum(value_field)).order_by(group_field)
    )
    return {
        "labels": [row[group_field] for row in rows],
        "values": [float(row["total"] or 0) for row in rows],
    }


def build_dashboard_stats(queryset):
    return {
        "customer_value": _breakdown(queryset, "customer_name", "total_invoice_value_with_gst"),
        "customer_qty": _breakdown(queryset, "customer_name", "qty"),
        "product_value": _breakdown(queryset, "product", "total_invoice_value_with_gst"),
    }

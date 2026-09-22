# =============================================================================
# billing — views.py
# Every view here is admin-only (core.decorators.admin_required).
# =============================================================================
import csv
import re

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.db.models.functions import Upper
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from core.decorators import admin_required

BULK_TOKEN_SPLIT_RE = re.compile(r"[\s,;]+")


def _parse_bulk_tokens(raw):
    """Splits a pasted block of Invoice No / Unique ID values (one per
    line, or comma/semicolon/whitespace separated) into a deduped list of
    non-empty, uppercased tokens for case-insensitive exact matching."""
    if not raw:
        return []
    tokens = {t.strip().upper() for t in BULK_TOKEN_SPLIT_RE.split(raw) if t.strip()}
    return sorted(tokens)

from .forms import BillingDataForm
from .models import BillingData
from .services.history import diff_and_record

# (key, column label) — single source of truth for the CSV export field
# picker, same "pick your columns" pattern as AIS140/crsc_calls.
EXPORT_COLUMNS = [
    ("unique_id", "Unique ID"),
    ("invoice_no", "Invoice No"),
    ("invoice_date", "Invoice Date"),
    ("upload_invoice", "Upload Invoice"),
    ("product", "Product"),
    ("qty", "Qty"),
    ("category", "Category"),
    ("part_sub_category", "Part Sub Category"),
    ("item_sub_category", "Item Sub Category"),
    ("part_no", "Part No"),
    ("customer_name", "Customer Name"),
    ("location", "Location"),
    ("invoice_value_without_gst", "Invoice Value (Without GST)"),
    ("total_invoice_value_with_gst", "Total Invoice Value (With GST)"),
    ("credited_amount", "Credited Amount"),
    ("tds_amount", "TDS Amount"),
    ("gap", "Gap"),
    ("theoretical_payment_due_date", "Theoretical Payment Due Date"),
    ("grn_no", "GRN No"),
    ("actual_grn_delivery_date", "Actual GRN Delivery Date"),
    ("due_date", "Due Date"),
    ("payment_status", "Payment Status"),
    ("received_date", "Received Date"),
    ("transporter_name", "Transporter Name"),
    ("docket_no", "Docket No"),
    ("date_of_shipment", "Date of Shipment"),
]
DEFAULT_EXPORT_KEYS = [key for key, _label in EXPORT_COLUMNS]


@admin_required
def add_billing_data(request, pk=None):
    instance = get_object_or_404(BillingData, pk=pk) if pk else None

    if request.method == "POST":
        form = BillingDataForm(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            previous = BillingData.objects.get(pk=instance.pk) if instance else None
            record = form.save()
            diff_and_record(record, previous, changed_by=request.user.username)
            messages.success(request, f"Invoice {record.unique_id} saved successfully.")
            return redirect("billing_add_detail", pk=record.pk)
        messages.error(request, "Please correct the errors below.")
    else:
        form = BillingDataForm(instance=instance)

    return render(request, "billing/invoice_form.html", {"form": form, "record": instance})


def _apply_filters(request, qs):
    """Shared by the dashboard and the CSV export so a download always
    matches whatever's currently filtered on screen."""
    search = (request.GET.get("invoice_no") or "").strip()
    customer_name = request.GET.get("customer_name")
    location = request.GET.get("location")
    payment_status = request.GET.get("payment_status")
    from_date = request.GET.get("from_date")
    to_date = request.GET.get("to_date")
    due_date_from = request.GET.get("due_date_from")
    due_date_to = request.GET.get("due_date_to")

    # Same search box does both a single free-text partial match and a bulk
    # paste of many Invoice No / Unique ID values (one per line, or
    # comma/semicolon/whitespace separated) — multiple tokens switch it to
    # an exact, case-insensitive match against both fields.
    bulk_tokens = _parse_bulk_tokens(search)
    if len(bulk_tokens) > 1:
        qs = qs.annotate(_inv_u=Upper("invoice_no"), _uid_u=Upper("unique_id")).filter(
            Q(_inv_u__in=bulk_tokens) | Q(_uid_u__in=bulk_tokens)
        )
    elif search:
        qs = qs.filter(Q(invoice_no__icontains=search) | Q(unique_id__icontains=search))

    if customer_name:
        qs = qs.filter(customer_name__icontains=customer_name)
    if location:
        qs = qs.filter(location__icontains=location)
    if payment_status:
        qs = qs.filter(payment_status=payment_status)
    if from_date:
        qs = qs.filter(invoice_date__gte=from_date)
    if to_date:
        qs = qs.filter(invoice_date__lte=to_date)
    if due_date_from:
        qs = qs.filter(due_date__gte=due_date_from)
    if due_date_to:
        qs = qs.filter(due_date__lte=due_date_to)

    return qs


@admin_required
def real_time_page(request):
    qs = BillingData.objects.all().order_by("-invoice_date")
    qs = _apply_filters(request, qs)

    invoice_no = (request.GET.get("invoice_no") or "").strip()
    customer_name = request.GET.get("customer_name")
    location = request.GET.get("location")
    payment_status = request.GET.get("payment_status")
    from_date = request.GET.get("from_date")
    to_date = request.GET.get("to_date")
    due_date_from = request.GET.get("due_date_from")
    due_date_to = request.GET.get("due_date_to")

    totals = qs.aggregate(
        total_value=Sum("total_invoice_value_with_gst"),
        total_qty=Sum("qty"),
    )

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page_obj,
        "totals": totals,
        "filter_qs": request.GET.urlencode(),
        "invoice_no": invoice_no or "", "customer_name": customer_name or "",
        "location": location or "", "payment_status": payment_status or "",
        "from_date": from_date or "", "to_date": to_date or "",
        "due_date_from": due_date_from or "", "due_date_to": due_date_to or "",
        "distinct_customers": BillingData.objects.order_by("customer_name")
                               .values_list("customer_name", flat=True).distinct(),
        "distinct_locations": BillingData.objects.order_by("location")
                               .values_list("location", flat=True).distinct(),
    }

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "billing/partials/results.html", context)
    return render(request, "billing/real_time_page.html", context)


@admin_required
def record_history_partial(request, pk):
    record = get_object_or_404(BillingData, pk=pk)
    history = record.history.all().order_by("-changed_at")
    return render(request, "billing/partials/history_modal.html", {"record": record, "history": history})


@admin_required
def export_page(request):
    """Field-picker screen. Carries the dashboard's current filters forward
    (as hidden inputs) so the export matches whatever's currently on screen."""
    carried = [(k, v) for k, v in request.GET.items() if k not in ("fields",)]
    return render(request, "billing/export_page.html", {
        "columns": EXPORT_COLUMNS,
        "default_keys": set(DEFAULT_EXPORT_KEYS),
        "carried_filters_list": carried,
    })


@admin_required
def download_csv(request):
    valid_keys = {key for key, _label in EXPORT_COLUMNS}
    selected_keys = [k for k in request.GET.getlist("fields") if k in valid_keys] or DEFAULT_EXPORT_KEYS
    selected_columns = [(key, label) for key, label in EXPORT_COLUMNS if key in selected_keys]

    qs = BillingData.objects.all().order_by("-invoice_date")
    qs = _apply_filters(request, qs)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="billing_export.csv"'
    writer = csv.writer(response)
    writer.writerow([label for _key, label in selected_columns])
    for record in qs:
        writer.writerow([getattr(record, key, "") or "" for key, _label in selected_columns])
    return response

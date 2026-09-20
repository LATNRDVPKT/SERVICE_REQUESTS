# =============================================================================
# billing — views.py
# Every view here is admin-only (core.decorators.admin_required).
# =============================================================================
import csv

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from core.decorators import admin_required

from .forms import BillingDataForm
from .models import BillingData
from .services.history import diff_and_record

EXPORT_FIELDS = [
    "unique_id", "invoice_no", "invoice_date", "product", "qty", "category",
    "part_sub_category", "item_sub_category", "part_no", "customer_name", "location",
    "invoice_value_without_gst", "total_invoice_value_with_gst", "credited_amount",
    "tds_amount", "gap", "theoretical_payment_due_date", "grn_no",
    "actual_grn_delivery_date", "due_date", "payment_status", "received_date",
    "transporter_name", "docket_no", "date_of_shipment",
]


@admin_required
def add_billing_data(request, pk=None):
    instance = get_object_or_404(BillingData, pk=pk) if pk else None

    if request.method == "POST":
        form = BillingDataForm(request.POST, instance=instance)
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


@admin_required
def real_time_page(request):
    qs = BillingData.objects.all().order_by("-invoice_date")

    invoice_no = request.GET.get("invoice_no")
    customer_name = request.GET.get("customer_name")
    location = request.GET.get("location")
    payment_status = request.GET.get("payment_status")
    from_date = request.GET.get("from_date")
    to_date = request.GET.get("to_date")
    due_date_from = request.GET.get("due_date_from")
    due_date_to = request.GET.get("due_date_to")

    if invoice_no:
        qs = qs.filter(invoice_no__icontains=invoice_no)
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
def download_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="billing_export.csv"'
    writer = csv.writer(response)
    writer.writerow(EXPORT_FIELDS)
    for record in BillingData.objects.all().order_by("-invoice_date"):
        writer.writerow([getattr(record, f, "") or "" for f in EXPORT_FIELDS])
    return response

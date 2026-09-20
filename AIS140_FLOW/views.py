# =============================================================================
# AIS140_FLOW — views.py
# =============================================================================
import csv
import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.utils.timezone import now, make_aware
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import datetime

from .constants import TERMINAL_STATUSES, COMPLETION_DATE_TRIGGER_STATUSES
from .forms import ManagerForm, PartBForm, PART_A_MANDATORY_LABELS
from .models import AIS140Request
from .services.darby import run_darby_lookup_and_save
from .services.email_utils import (
    send_part_a_assignment_email, send_request_remark_email,
    send_completion_email, send_remarks_updated_email,
)
from .services.ialert import push_update_to_ialert, IAlertPushError
from .services.latest_update import get_latest_ticket_update
from .services.workflow import apply_part_b_business_rules, write_history_rows
from .services.export import EXPORT_COLUMNS, DEFAULT_SELECTED_KEYS, build_row, selected_columns
from .services.dashboard_stats import build_dashboard_stats

logger = logging.getLogger(__name__)


# =============================================================================
# Part-A — Manager ticket creation / edit
# =============================================================================
@login_required
def part_a_form(request, ticket_id=None):
    instance = get_object_or_404(AIS140Request, pk=ticket_id) if ticket_id else None
    is_new = instance is None

    if request.method == "POST":
        form = ManagerForm(request.POST, instance=instance)
        if form.is_valid():
            ticket = form.save(commit=False)
            if is_new:
                ticket.date_of_request = ticket.date_of_request or now()
                ticket.ticket_through = ticket.ticket_through or "Manual"
            previous_engineer = instance.assigned_engineer_email if instance else None
            ticket.save()

            if ticket.assigned_engineer_email and ticket.assigned_engineer_email not in ("--", ""):
                if is_new or ticket.assigned_engineer_email != previous_engineer:
                    part_b_url = request.build_absolute_uri(
                        reverse("part_b_form", args=[ticket.id])
                    )
                    send_part_a_assignment_email(ticket, part_b_url)

            # REQ-13 — Darby auto-lookup right after ticket creation
            if is_new:
                run_darby_lookup_and_save(ticket)

            messages.success(request, f"Ticket {ticket.unique_id} saved successfully.")
            return redirect("part_a_form_edit", ticket_id=ticket.id)
        else:
            missing = [
                PART_A_MANDATORY_LABELS[f] for f in PART_A_MANDATORY_LABELS if f in form.errors
            ]
            if missing:
                messages.error(request, "Please fill the mandatory fields: " + ", ".join(missing))
    else:
        form = ManagerForm(instance=instance)

    return render(request, "AIS140_FLOW/part_a_form.html", {
        "form": form, "ticket": instance, "is_new": is_new,
    })


# =============================================================================
# Part-B — Engineer resolution workflow
# =============================================================================
@login_required
def part_b_form(request, ticket_id):
    ticket = get_object_or_404(AIS140Request, pk=ticket_id)
    read_only = ticket.completion_status in TERMINAL_STATUSES

    if request.method == "POST" and not read_only:
        form = PartBForm(request.POST, request.FILES, instance=ticket)
        if form.is_valid():
            updated = form.save(commit=False)

            previous = AIS140Request.objects.get(pk=ticket.pk)
            history_rows = apply_part_b_business_rules(updated, previous)

            was_terminal = previous.completion_status in TERMINAL_STATUSES
            becomes_terminal = updated.completion_status in TERMINAL_STATUSES
            if not was_terminal and updated.completion_status in COMPLETION_DATE_TRIGGER_STATUSES:
                updated.completion_date = now()

            try:
                with transaction.atomic():
                    if previous.request_id:
                        push_update_to_ialert(updated, form_files=request.FILES)
                    updated.save()
                    write_history_rows(updated, history_rows)
            except IAlertPushError as exc:
                messages.error(request, f"iAlert rejected this update — nothing was saved. ({exc})")
                return redirect("part_b_form", ticket_id=ticket.id)

            part_b_url = request.build_absolute_uri(reverse("part_b_form", args=[updated.id]))
            send_request_remark_email(updated, part_b_url)
            if not was_terminal and becomes_terminal:
                send_completion_email(updated)

            messages.success(request, "Ticket updated successfully.")
            return redirect("part_b_form", ticket_id=updated.id)
    else:
        form = PartBForm(instance=ticket)

    return render(request, "AIS140_FLOW/part_b_form.html", {
        "form": form, "ticket": ticket, "read_only": read_only,
    })


# =============================================================================
# Real-Time dashboard
# =============================================================================
REALTIME_PAGE_SIZE = 25


def _parse_date_range(request, from_key, to_key):
    """Returns (from_date, to_date) as aware datetimes, or (None, None)."""
    from_raw = request.GET.get(from_key)
    to_raw = request.GET.get(to_key)
    from_dt = to_dt = None
    if from_raw:
        d = parse_date(from_raw)
        if d:
            from_dt = make_aware(datetime.datetime.combine(d, datetime.time.min))
    if to_raw:
        d = parse_date(to_raw)
        if d:
            to_dt = make_aware(datetime.datetime.combine(d, datetime.time.max))
    return from_dt, to_dt


def _apply_dashboard_filters(request, qs):
    state = request.GET.get("state")
    completion_status = request.GET.get("completion_status")
    search = request.GET.get("q")

    if state:
        qs = qs.filter(state__iexact=state)
    if completion_status:
        qs = qs.filter(completion_status=completion_status)
    if search:
        qs = qs.filter(unique_id__icontains=search) | qs.filter(vin_no__icontains=search)

    req_from, req_to = _parse_date_range(request, "request_date_from", "request_date_to")
    if req_from:
        qs = qs.filter(date_of_request__gte=req_from)
    if req_to:
        qs = qs.filter(date_of_request__lte=req_to)

    comp_from, comp_to = _parse_date_range(request, "completion_date_from", "completion_date_to")
    if comp_from:
        qs = qs.filter(completion_date__gte=comp_from)
    if comp_to:
        qs = qs.filter(completion_date__lte=comp_to)

    return qs


@login_required
def real_time_page(request):
    qs = AIS140Request.objects.all().order_by("-date_of_request")
    qs = _apply_dashboard_filters(request, qs)

    stats = build_dashboard_stats(qs)

    paginator = Paginator(qs, REALTIME_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))

    rows = []
    for ticket in page_obj.object_list:
        latest = get_latest_ticket_update(ticket)
        rows.append({"ticket": ticket, "latest": latest})

    filter_qs = request.GET.urlencode()

    context = {
        "rows": rows,
        "page_obj": page_obj,
        "state": request.GET.get("state", ""),
        "completion_status": request.GET.get("completion_status", ""),
        "search": request.GET.get("q", ""),
        "request_date_from": request.GET.get("request_date_from", ""),
        "request_date_to": request.GET.get("request_date_to", ""),
        "completion_date_from": request.GET.get("completion_date_from", ""),
        "completion_date_to": request.GET.get("completion_date_to", ""),
        "filter_qs": filter_qs,
        "distinct_states": AIS140Request.objects.order_by("state")
                            .values_list("state", flat=True).distinct(),
        "stats": stats,
        "stats_json": json.dumps(stats),
    }

    # Live-filter AJAX requests only need the results fragment (table +
    # pagination + chart data) re-rendered, not the whole page.
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "AIS140_FLOW/partials/dashboard_results.html", context)

    return render(request, "AIS140_FLOW/real_time_page.html", context)


@login_required
def ticket_history_partial(request, ticket_id):
    """REQ-10 — eye-icon drill-down: full AIS140RequestUpdate trail for one ticket."""
    ticket = get_object_or_404(AIS140Request, pk=ticket_id)
    history = ticket.history.all().order_by("-remark_datetime")
    return render(request, "AIS140_FLOW/partials/history_modal.html", {
        "ticket": ticket, "history": history,
    })


# =============================================================================
# CSV export — single, field-selectable
# =============================================================================
@login_required
def export_page(request):
    """Field-picker screen. Carries the dashboard's current filters forward
    (as hidden inputs) so the export matches whatever's currently on screen."""
    carried = [(k, v) for k, v in request.GET.items() if k not in ("fields",)]
    return render(request, "AIS140_FLOW/export_page.html", {
        "columns": EXPORT_COLUMNS,
        "default_keys": set(DEFAULT_SELECTED_KEYS),
        "carried_filters_list": carried,
    })


@login_required
def download_csv(request):
    selected_keys = request.GET.getlist("fields") or DEFAULT_SELECTED_KEYS
    valid_keys = {c[0] for c in EXPORT_COLUMNS}
    selected_keys = [k for k in selected_keys if k in valid_keys] or DEFAULT_SELECTED_KEYS

    qs = AIS140Request.objects.all().order_by("-date_of_request")
    qs = _apply_dashboard_filters(request, qs)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="ais140_export.csv"'
    writer = csv.writer(response)
    writer.writerow([label for _key, label in selected_columns(selected_keys)])
    for ticket in qs:
        writer.writerow(build_row(ticket, set(selected_keys)))
    return response


# =============================================================================
# External API intake (Ashok Leyland / iAlert)
# =============================================================================
REQUIRED_API_FIELDS = [
    "request_id", "request_date", "state", "chassis_number", "engine_no", "obu_id",
    "vehicle_reg_no", "vehicle_model", "customer_name", "customer_mobile_number",
    "pan_no", "aadhar_no", "mfg_year", "rto_name", "rto_code", "dealer_name", "dealer_code",
]


@csrf_exempt
@require_http_methods(["POST"])
def api_create_ais140_ticket(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    missing = [f for f in REQUIRED_API_FIELDS if not data.get(f)]
    if missing:
        return JsonResponse({"error": "Missing required fields.", "fields": missing}, status=400)

    ticket = AIS140Request.objects.create(
        request_id=data["request_id"],
        date_of_request=now(),
        Customer_assigned_date=now(),
        state=data["state"],
        vin_no=data["chassis_number"],
        engine=data["engine_no"],
        psn=data["obu_id"],
        vehicle_no=data["vehicle_reg_no"],
        vehicle_model=data["vehicle_model"],
        customer_name=data["customer_name"],
        customer_phone=data["customer_mobile_number"],
        Customer_mobile_number=data["customer_mobile_number"],
        Customer_Alternate_number=data.get("customer_alternate_number"),
        Customer_Email_ID=data.get("customer_email_id"),
        Cust_veh_Regn_Address=data.get("cust_veh_regn_address"),
        Cust_veh_Regn_Pincode=data.get("cust_veh_regn_pincode"),
        pan_card=data["pan_no"],
        aadhar_card=data["aadhar_no"],
        manufacturing_year=data["mfg_year"],
        request_type=data.get("ais140_type"),
        AIS140_Type=(data.get("ais140_type") or "").strip().title(),
        rto_name=data["rto_name"],
        rto_code=data["rto_code"],
        dealer_name=data["dealer_name"],
        dealer_code=data["dealer_code"],
        Dealer_Contact=data.get("dealer_contact"),
        Dealer_Location=data.get("dealer_location"),
        Dealer_mail=data.get("dealer_email_id"),
        TSM_mail=data.get("tsm_email_id"),
        Ialert_Email_ID=data.get("ialert_email_id"),
        zone=data.get("zoneName"),
        category=data.get("category"),
        ticket_through="A.L API",
        assigned_engineer_email="--",
    )

    # REQ-13 — Darby auto-lookup right after ticket creation
    run_darby_lookup_and_save(ticket)

    return JsonResponse({"unique_id": ticket.unique_id, "id": ticket.id}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def api_update_ais140_remarks(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    request_id = data.get("request_id")
    if not request_id:
        return JsonResponse({"error": "request_id is required."}, status=400)

    try:
        ticket = AIS140Request.objects.get(request_id=request_id)
    except AIS140Request.DoesNotExist:
        raise Http404("No ticket found for that request_id.")

    ticket.AL_remarks = data.get("al_remarks", ticket.AL_remarks)
    ticket.AL_comments = data.get("al_comments", ticket.AL_comments)
    ticket.al_remarks_updated_at = now()
    ticket.save(update_fields=["AL_remarks", "AL_comments", "al_remarks_updated_at"])

    write_history_rows(ticket, [{
        "source_field": "al_remarks", "latest_remark": ticket.AL_remarks,
        "latest_comments": ticket.AL_comments, "remark_datetime": ticket.al_remarks_updated_at,
        "attending_engineer": ticket.attending_engineer,
    }])

    send_remarks_updated_email(ticket)
    return JsonResponse({"status": "ok", "unique_id": ticket.unique_id})


@login_required
def fetch_darby_communication_ais140(request, ticket_id):
    """Manual re-trigger of the Darby lookup for one ticket (kept for support use)."""
    ticket = get_object_or_404(AIS140Request, pk=ticket_id)
    success = run_darby_lookup_and_save(ticket)
    ticket.refresh_from_db()
    return JsonResponse({
        "success": success,
        "status": ticket.darby_lookup_status,
        "iccid": ticket.icicid_no,
        "imei": ticket.imei_no,
        "product_code": ticket.device_product_code,
        "architecture_type": ticket.device_architecture_type,
        "battery_voltage": ticket.device_battery_voltage,
    })


@login_required
def success_page(request):
    return render(request, "AIS140_FLOW/success.html")

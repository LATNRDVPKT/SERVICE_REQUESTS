# =============================================================================
# crsc_calls — views.py
# =============================================================================
import csv
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.utils.timezone import now, make_aware
import datetime

from accounts.models import UserProfile
from .forms import ManagerForm, EngineerForm, PART_A_MANDATORY_LABELS, OTHERS_FIELD_PAIRS
from .models import DirectCall, FIR_CLOSURE_STATUSES, CALL_STATUS_CHOICES
from .services.darby import run_darby_lookup_and_save
from .services.dashboard_stats import build_dashboard_stats
from .services.email_utils import send_assignment_email, send_customer_email, send_fir_approval_email
from .services.export import EXPORT_COLUMNS, build_row, export_headers
from .services.latest_update import get_latest_call_update
from .services.workflow import apply_follow_up_rules, write_history_rows


def _user_role(user):
    profile = getattr(user, "profile", None)
    return profile.role if profile else "engineer"


def _engineer_choices():
    return [
        (p.display_name, p.display_name)
        for p in UserProfile.objects.filter(role="engineer").order_by("display_name")
    ]


def _apply_others_fields(post_data):
    """
    Mirrors the original manager_form()'s dropdown_fields handling: if a
    dropdown value is 'others', substitute the companion free-text field.
    """
    data = post_data.copy()
    for field, other_field in OTHERS_FIELD_PAIRS.items():
        if data.get(field) == "others":
            data[field] = data.get(other_field) or "others"
    return data


# =============================================================================
# Part-A — Manager intake
# =============================================================================
@login_required
def manager_form(request, call_id=None):
    entry = get_object_or_404(DirectCall, pk=call_id) if call_id else None
    is_new = entry is None

    if request.method == "POST":
        post_data = _apply_others_fields(request.POST)
        form = ManagerForm(post_data, request.FILES, instance=entry, engineer_choices=_engineer_choices())
        if form.is_valid():
            call = form.save(commit=False)
            if is_new:
                call.date_of_complaint = now()
            previous_assignee = entry.complaint_assigned_to if entry else None
            call.save()

            if is_new:
                run_darby_lookup_and_save(call)

            if call.submitted_to_email and (is_new or call.complaint_assigned_to != previous_assignee):
                part_b_url = request.build_absolute_uri(reverse("crsc_engineer_form", args=[call.id]))
                send_assignment_email(call, part_b_url)
                send_customer_email(call)

            messages.success(request, f"Call {call.unique_id} saved successfully.")
            return redirect("crsc_manager_form_edit", call_id=call.id)
        else:
            missing = [PART_A_MANDATORY_LABELS[f] for f in PART_A_MANDATORY_LABELS if f in form.errors]
            if missing:
                messages.error(request, "Please fill the mandatory fields: " + ", ".join(missing))
    else:
        form = ManagerForm(instance=entry, engineer_choices=_engineer_choices())

    return render(request, "crsc_calls/manager_form.html", {"form": form, "call": entry, "is_new": is_new})


# =============================================================================
# Part-B — Engineer resolution
# =============================================================================
@login_required
def engineer_form(request, call_id):
    call = get_object_or_404(DirectCall, pk=call_id)
    role = _user_role(request.user)

    if request.method == "POST":
        form = EngineerForm(request.POST, request.FILES, instance=call, role=role, call_type=call.call_type)
        if form.is_valid():
            updated = form.save(commit=False)

            previous = DirectCall.objects.get(pk=call.pk)
            history_rows = apply_follow_up_rules(updated, previous)

            was_fir = previous.call_status == "FIR - For approval"
            updated.save()
            write_history_rows(updated, history_rows)

            if updated.call_status in FIR_CLOSURE_STATUSES and role == "admin":
                recipients = [e for e in [updated.submitted_to_email] if e]
                send_fir_approval_email(updated, recipients)

            messages.success(request, "Call updated successfully.")
            return redirect("crsc_engineer_form", call_id=updated.id)
    else:
        form = EngineerForm(instance=call, role=role, call_type=call.call_type)

    return render(request, "crsc_calls/engineer_form.html", {"form": form, "call": call, "role": role})


# =============================================================================
# Real-Time dashboard
# =============================================================================
PAGE_SIZE = 25


def _parse_date_range(request, from_key, to_key):
    from_raw, to_raw = request.GET.get(from_key), request.GET.get(to_key)
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


def _apply_filters(request, qs):
    call_status = request.GET.get("call_status")
    call_type = request.GET.get("call_type")
    engineer = request.GET.get("engineer")
    ialert_ticket_no = request.GET.get("ialert_ticket_no")
    vin_q = request.GET.get("vin")
    psn_q = request.GET.get("psn")
    unique_id_q = request.GET.get("unique_id")

    if call_status:
        qs = qs.filter(call_status=call_status)
    if call_type:
        qs = qs.filter(call_type=call_type)
    if engineer:
        qs = qs.filter(complaint_assigned_to=engineer)
    if ialert_ticket_no:
        qs = qs.filter(ialert_ticket_no__icontains=ialert_ticket_no)
    if unique_id_q:
        qs = qs.filter(unique_id__icontains=unique_id_q)
    # VIN/PSN typeahead — only starts filtering once 5+ characters typed
    if vin_q and len(vin_q.strip()) >= 5:
        qs = qs.filter(vin__icontains=vin_q.strip())
    if psn_q and len(psn_q.strip()) >= 5:
        qs = qs.filter(psn__icontains=psn_q.strip())

    comp_from, comp_to = _parse_date_range(request, "complaint_date_from", "complaint_date_to")
    if comp_from:
        qs = qs.filter(date_of_complaint__gte=comp_from)
    if comp_to:
        qs = qs.filter(date_of_complaint__lte=comp_to)

    closure_from, closure_to = _parse_date_range(request, "closure_date_from", "closure_date_to")
    if closure_from:
        qs = qs.filter(date_of_closure__gte=closure_from)
    if closure_to:
        qs = qs.filter(date_of_closure__lte=closure_to)

    return qs


@login_required
def real_time_page(request):
    qs = DirectCall.objects.all().order_by("-date_of_complaint")
    qs = _apply_filters(request, qs)

    stats = build_dashboard_stats(qs)

    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))

    rows = [{"call": c, "latest": get_latest_call_update(c)} for c in page_obj.object_list]

    context = {
        "rows": rows,
        "page_obj": page_obj,
        "filter_qs": request.GET.urlencode(),
        "call_status": request.GET.get("call_status", ""),
        "call_type": request.GET.get("call_type", ""),
        "engineer": request.GET.get("engineer", ""),
        "ialert_ticket_no": request.GET.get("ialert_ticket_no", ""),
        "vin": request.GET.get("vin", ""),
        "psn": request.GET.get("psn", ""),
        "unique_id": request.GET.get("unique_id", ""),
        "complaint_date_from": request.GET.get("complaint_date_from", ""),
        "complaint_date_to": request.GET.get("complaint_date_to", ""),
        "closure_date_from": request.GET.get("closure_date_from", ""),
        "closure_date_to": request.GET.get("closure_date_to", ""),
        "engineer_choices": _engineer_choices(),
        "call_status_choices": CALL_STATUS_CHOICES,
        "stats": stats,
        "stats_json": json.dumps(stats),
    }

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "crsc_calls/partials/dashboard_results.html", context)
    return render(request, "crsc_calls/real_time_page.html", context)


@login_required
def call_history_partial(request, call_id):
    call = get_object_or_404(DirectCall, pk=call_id)
    history = call.history.all().order_by("-event_datetime")
    return render(request, "crsc_calls/partials/history_modal.html", {"call": call, "history": history})


@login_required
def download_csv(request):
    qs = DirectCall.objects.all().order_by("-date_of_complaint")
    qs = _apply_filters(request, qs)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="crsc_calls_export.csv"'
    writer = csv.writer(response)
    writer.writerow(export_headers())
    for call in qs:
        writer.writerow(build_row(call))
    return response

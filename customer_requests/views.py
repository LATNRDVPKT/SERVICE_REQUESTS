import csv
import json
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models.functions import Upper
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.html import format_html
from django.utils.timezone import now, make_aware, is_naive
import datetime

from accounts.models import UserProfile
from core.decorators import admin_required
from .constants import resolve_engineer_contact, resolve_fir_pdf_recipient, RESPONSIBILITY_CHOICES
from .forms import ManagerForm, EngineerForm, PlantForm, PART_A_MANDATORY_LABELS
from .models import DirectCall, FIR_CLOSURE_STATUSES, CUSTOMER_CLOSURE_STATUSES, CALL_STATUS_CHOICES
from .services.darby import run_darby_lookup_and_save
from .services.dashboard_stats import build_dashboard_stats, call_type_values
from .services.ialert import push_follow_up_to_ialert, IAlertPushError
from .services.email_utils import (
    send_assignment_email, send_customer_email, send_fir_approval_email,
    send_remark_updated_email, send_customer_remark_email, send_closure_email, send_fir_pdf_email,
    send_feedback_email,
)
from .services.feedback import make_feedback_token, read_feedback_token
from .services.latest_update import get_latest_call_update
from .services.plant import PLANT_COLUMNS, PLANT_EDIT_KEYS, PLANT_LOCATIONS, PLANT_READONLY_FIELDS
from .services.report_columns import DEFAULT_EXPORT_KEYS, REPORT_COLUMNS, build_report_row, report_headers
from .services.tat import compute_tats
from .services.workflow import apply_follow_up_rules, write_history_rows

def _user_role(user):
    profile = getattr(user, "profile", None)
    return profile.role if profile else "engineer"

def _engineer_choices():
    return [
        (p.display_name, p.display_name)
        for p in UserProfile.objects.filter(role="engineer").order_by("display_name")
    ]

def _display_name(user):
    profile = getattr(user, "profile", None)
    if profile and profile.display_name:
        return profile.display_name
    return user.get_username()

def _flash_form_errors(request, form):
    """Flashes every validation error with its field label, so the user
    always sees a clear reason the form didn't submit."""
    for field_name, errors in form.errors.items():
        if field_name == "__all__":
            label = None
        elif field_name in form:
            label = form[field_name].label
        else:
            label = field_name
        for err in errors:
            messages.error(request, f"{label}: {err}" if label else err)

@admin_required(message="New/edit CRSC calls (Ticket Creation form) is restricted to admin users.")
def manager_form(request, call_id=None):
    entry = get_object_or_404(DirectCall, pk=call_id) if call_id else None
    is_new = entry is None

    if request.method == "POST":
        form = ManagerForm(request.POST, request.FILES, instance=entry, engineer_choices=_engineer_choices())
        if form.is_valid():
            call = form.save(commit=False)
            if is_new:
                call.date_of_complaint = now()
                call.responsibility = "DANLAW"

            call.complaint_received_by = _display_name(request.user)
            previous_assignee = entry.complaint_assigned_to if entry else None
            call.submitted_to_email, call.engineer_contact_number = resolve_engineer_contact(
                call.complaint_assigned_to
            )

            if call.complaint_assigned_to and not call.assigned_date:
                call.assigned_date = now()
            compute_tats(call)
            call.save()

            if is_new:
                run_darby_lookup_and_save(call)

            if call.submitted_to_email and (is_new or call.complaint_assigned_to != previous_assignee):
                engineer_form_url = request.build_absolute_uri(reverse("crsc_engineer_form", args=[call.id]))
                send_assignment_email(call, engineer_form_url)
                send_customer_email(call)

            messages.success(request, f"Call {call.unique_id} saved successfully.")
            return redirect("crsc_manager_form_edit", call_id=call.id)
        else:
            _flash_form_errors(request, form)
    else:
        form = ManagerForm(instance=entry, engineer_choices=_engineer_choices())

    return render(request, "customer_requests/manager_form.html", {"form": form, "call": entry, "is_new": is_new})

def customer_feedback(request, token):
    """Public (no login) page the customer reaches from the feedback e-mail.
    The link is a signed, expiring token — see services/feedback.py."""
    tpl = "customer_requests/feedback.html"
    call_id = read_feedback_token(token)
    call = DirectCall.objects.filter(pk=call_id).first() if call_id else None
    if call is None:
        return render(request, tpl, {"invalid": True}, status=404)

    if call.feedback_submission_datetime:
        return render(request, tpl, {"direct_call": call, "submitted": True})

    if request.method == "POST":
        confirmation = request.POST.get("confirmation", "")
        satisfaction = request.POST.get("feedback", "")
        rating = request.POST.get("rating", "")
        comment = (request.POST.get("customer_feedback") or "").strip()[:250]
        if (
            confirmation not in {"Resolved", "Pending"}
            or satisfaction not in {"Satisfied", "Not Satisfied"}
            or rating not in {"1", "2", "3", "4", "5"}
            or not comment
        ):
            return render(request, tpl, {
                "direct_call": call, "error": "Please answer every question before submitting.",
            })
        call.customer_confirmation = confirmation
        call.customer_satisfaction = satisfaction
        call.rating = int(rating)
        call.customer_feedback = comment
        call.feedback_submission_datetime = now()
        call.save(update_fields=[
            "customer_confirmation", "customer_satisfaction", "rating",
            "customer_feedback", "feedback_submission_datetime",
        ])
        return render(request, tpl, {"direct_call": call, "submitted": True})

    return render(request, tpl, {"direct_call": call})


@login_required
def engineer_form(request, call_id):
    call = get_object_or_404(DirectCall, pk=call_id)
    role = _user_role(request.user)

    if request.method == "POST":
        form = EngineerForm(request.POST, request.FILES, instance=call, role=role, call_type=call.call_type)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.follow_up_engineer = _display_name(request.user)


            previous = DirectCall.objects.get(pk=call.pk)
            history_rows = apply_follow_up_rules(updated, previous)
            compute_tats(updated)

            if updated.call_type == "iAlert Call":
                try:
                    push_follow_up_to_ialert(updated)
                except IAlertPushError as exc:
                    messages.error(request, f"Not submitted — AL iAlert API rejected this update: {exc}")
                    return render(request, "customer_requests/engineer_form.html", {"form": form, "call": call, "role": role})

            was_fir = previous.call_status == "FIR - For approval"
            updated.save()
            write_history_rows(updated, history_rows)

            engineer_form_url = request.build_absolute_uri(reverse("crsc_engineer_form", args=[updated.id]))

            if updated.call_status in FIR_CLOSURE_STATUSES and role == "admin":
                recipients = [e for e in [updated.submitted_to_email] if e]
                send_fir_approval_email(updated, recipients, engineer_form_url)

            # Engineer gets a copy of every new follow-up round they log.
            if any(row["source_field"] == "follow_up" for row in history_rows):
                send_remark_updated_email(updated, engineer_form_url)
                send_customer_remark_email(updated)

            # Signed link to the public feedback page - used by both the
            # closure mail's "Provide Feedback" button and the feedback mail.
            feedback_url = request.build_absolute_uri(
                reverse("crsc_feedback", args=[make_feedback_token(updated.id)])
            )

            # Customer is notified again the first time the call reaches
            if (
                updated.call_status != previous.call_status
                and updated.call_status in CUSTOMER_CLOSURE_STATUSES
            ):
                send_closure_email(updated, feedback_url)

            # Feedback is requested from the customer once per call, the
            # first time it is saved with any status other than "Pending".
            if updated.call_status != "Pending" and not previous.feedback_requested_at:
                if send_feedback_email(updated, feedback_url):
                    updated.feedback_requested_at = now()
                    updated.save(update_fields=["feedback_requested_at"])

            # FIR summary PDF goes to the location handling the device,
            if (
                updated.call_status != previous.call_status
                and updated.call_status in FIR_CLOSURE_STATUSES
            ):
                recipient = resolve_fir_pdf_recipient(updated.device_to_be_sent)
                send_fir_pdf_email(updated, recipient)

            messages.success(request, "Call updated successfully.")
            return redirect("crsc_engineer_form", call_id=updated.id)
        else:
            _flash_form_errors(request, form)
    else:
        form = EngineerForm(instance=call, role=role, call_type=call.call_type)

    return render(request, "customer_requests/engineer_form.html", {"form": form, "call": call, "role": role})

PAGE_SIZE = 25

ASSIGNED_TO_COLUMN_INDEX = [key for key, _label in REPORT_COLUMNS].index("complaint_assigned_to")

BULK_TOKEN_SPLIT_RE = re.compile(r"[\s,;]+")

def _parse_bulk_tokens(raw):
    """Splits a pasted block of VIN / PSN / Unique ID values (one per line,
    or comma/semicolon/whitespace separated) into a deduped list of
    non-empty, uppercased tokens for case-insensitive exact matching."""
    if not raw:
        return []
    tokens = {t.strip().upper() for t in BULK_TOKEN_SPLIT_RE.split(raw) if t.strip()}
    return sorted(tokens)

def _parse_datetime_local(raw):
    if not raw:
        return None
    dt = parse_datetime(raw)
    if dt:
        return make_aware(dt) if is_naive(dt) else dt
    d = parse_date(raw)
    if d:
        return make_aware(datetime.datetime.combine(d, datetime.time.min))
    return None

def _parse_date_range(request, from_key, to_key):
    return _parse_datetime_local(request.GET.get(from_key)), _parse_datetime_local(request.GET.get(to_key))

SEARCH_FIELD_CHOICES = [
    ("unique_id", "Unique ID"),
    ("vin", "VIN"),
    ("psn", "PSN"),
]
SEARCH_FIELD_LOOKUP = {"unique_id": "unique_id", "vin": "vin", "psn": "psn"}

def _apply_filters(request, qs):
    call_status = request.GET.get("call_status")
    call_type = request.GET.get("call_type")
    engineer = request.GET.get("engineer")
    responsibility = request.GET.get("responsibility")
    ialert_ticket_no = request.GET.get("ialert_ticket_no")
    search_field = SEARCH_FIELD_LOOKUP.get(request.GET.get("search_field"), "unique_id")
    search_value = (request.GET.get("search_value") or "").strip()
    bulk_tokens = _parse_bulk_tokens(search_value)

    if call_status:
        qs = qs.filter(call_status=call_status)
    if call_type:
        qs = qs.filter(call_type__in=call_type_values(call_type))
    if engineer:
        qs = qs.filter(complaint_assigned_to=engineer)
    if responsibility:
        qs = qs.filter(responsibility=responsibility)
    if ialert_ticket_no:
        qs = qs.filter(ialert_ticket_no__icontains=ialert_ticket_no)

    if len(bulk_tokens) > 1:
        qs = qs.annotate(_search_u=Upper(search_field)).filter(_search_u__in=bulk_tokens)
    elif search_value:
        qs = qs.filter(**{f"{search_field}__icontains": search_value})

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

    rows = []
    for c in page_obj.object_list:
        latest = get_latest_call_update(c)
        cells = build_report_row(c, latest)

        if cells[ASSIGNED_TO_COLUMN_INDEX] in ("", "--", None):
            cells[ASSIGNED_TO_COLUMN_INDEX] = format_html(
                '<a href="{}" title="Assign an engineer">--</a>',
                reverse("crsc_manager_form_edit", args=[c.id]),
            )
        rows.append({"call": c, "latest": latest, "cells": cells})

    context = {
        "rows": rows,
        "columns": REPORT_COLUMNS,
        "page_obj": page_obj,
        "filter_qs": request.GET.urlencode(),
        "call_status": request.GET.get("call_status", ""),
        "call_type": request.GET.get("call_type", ""),
        "engineer": request.GET.get("engineer", ""),
        "responsibility": request.GET.get("responsibility", ""),
        "responsibility_choices": RESPONSIBILITY_CHOICES,
        "ialert_ticket_no": request.GET.get("ialert_ticket_no", ""),
        "search_field": request.GET.get("search_field", "unique_id"),
        "search_value": request.GET.get("search_value", ""),
        "search_field_choices": SEARCH_FIELD_CHOICES,
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
        return render(request, "customer_requests/partials/dashboard_results.html", context)
    return render(request, "customer_requests/real_time_page.html", context)

@login_required
def call_history_partial(request, call_id):
    call = get_object_or_404(DirectCall, pk=call_id)
    history = call.history.all().order_by("-event_datetime")
    return render(request, "customer_requests/partials/history_modal.html", {"call": call, "history": history})


@login_required
def export_page(request):
    
    carried = [(k, v) for k, v in request.GET.items() if k not in ("fields",)]
    return render(request, "customer_requests/export_page.html", {
        "columns": REPORT_COLUMNS,
        "default_keys": set(DEFAULT_EXPORT_KEYS),
        "carried_filters_list": carried,
    })

@login_required
def download_csv(request):
    valid_keys = {key for key, _label in REPORT_COLUMNS}
    selected_keys = [k for k in request.GET.getlist("fields") if k in valid_keys] or DEFAULT_EXPORT_KEYS

    qs = DirectCall.objects.all().order_by("-date_of_complaint")
    qs = _apply_filters(request, qs)
    current_ist_timestamp = now().strftime("%Y%m%d_%H%M%S")
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="crsc_calls_export_{current_ist_timestamp}.csv"'
    writer = csv.writer(response)
    writer.writerow(report_headers(selected_keys))
    for call in qs:
        writer.writerow(build_report_row(call, get_latest_call_update(call), selected_keys))
    return response


# =============================================================================
# Plant logins (Hyderabad / Goa)
# =============================================================================
def _plant_calls(request):
    """Calls this user may see on the plant screens: a plant login gets only
    the calls whose Faulty Device Sent to Location is their plant; an admin
    sees every plant call (optionally narrowed with ?plant=). Anyone else is
    refused."""
    role = _user_role(request.user)
    qs = DirectCall.objects.all().order_by("-date_of_complaint")
    if role == "plant":
        location = getattr(request.user.profile, "plant_location", "") or ""
        return qs.filter(device_to_be_sent=location) if location else qs.none()
    if role == "admin":
        wanted = request.GET.get("plant")
        if wanted in PLANT_LOCATIONS:
            return qs.filter(device_to_be_sent=wanted)
        return qs.filter(device_to_be_sent__in=PLANT_LOCATIONS)
    raise PermissionDenied


def _plant_cell(call, key):
    value = getattr(call, key, "")
    if value in (None, ""):
        return ""
    if key == "device_shipped_date":
        return value.strftime("%d-%m-%Y")
    return value


@login_required
def plant_dashboard(request):
    qs = _apply_filters(request, _plant_calls(request))
    page_obj = Paginator(qs, PAGE_SIZE).get_page(request.GET.get("page"))
    rows = [
        {"call": c, "cells": [_plant_cell(c, key) for key, _label in PLANT_COLUMNS]}
        for c in page_obj.object_list
    ]
    return render(request, "customer_requests/plant_dashboard.html", {
        "rows": rows,
        "columns": PLANT_COLUMNS,
        "page_obj": page_obj,
        "filter_qs": request.GET.urlencode(),
        "search_field": request.GET.get("search_field", "unique_id"),
        "search_value": request.GET.get("search_value", ""),
        "search_field_choices": SEARCH_FIELD_CHOICES,
        "location": getattr(request.user.profile, "plant_location", ""),
    })


@login_required
def plant_form(request, call_id):
    call = get_object_or_404(_plant_calls(request), pk=call_id)

    if request.method == "POST":
        form = PlantForm(request.POST, instance=call)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.save(update_fields=PLANT_EDIT_KEYS)
            messages.success(request, f"Plant update saved for {call.unique_id}.")
            return redirect("crsc_plant_form", call_id=call.id)
        _flash_form_errors(request, form)
    else:
        form = PlantForm(instance=call)

    readonly = [(label, _plant_cell(call, key)) for key, label in PLANT_READONLY_FIELDS]
    return render(request, "customer_requests/plant_form.html", {"form": form, "call": call, "readonly": readonly})


@login_required
def plant_download_csv(request):
    qs = _apply_filters(request, _plant_calls(request))
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="crsc_plant_export_{now().strftime("%Y%m%d_%H%M%S")}.csv"'
    )
    writer = csv.writer(response)
    writer.writerow([label for _key, label in PLANT_COLUMNS])
    for call in qs:
        writer.writerow([_plant_cell(call, key) for key, _label in PLANT_COLUMNS])
    return response

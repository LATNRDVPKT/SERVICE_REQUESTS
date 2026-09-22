# =============================================================================
# crsc_calls — views.py
# =============================================================================
import csv
import json
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models.functions import Upper
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.timezone import now, make_aware, is_naive
import datetime

from accounts.models import UserProfile
from core.decorators import admin_required
from .constants import resolve_engineer_contact, resolve_fir_pdf_recipient, RESPONSIBILITY_CHOICES
from .forms import ManagerForm, EngineerForm, PART_A_MANDATORY_LABELS
from .models import DirectCall, FIR_CLOSURE_STATUSES, CUSTOMER_CLOSURE_STATUSES, CALL_STATUS_CHOICES
from .services.darby import run_darby_lookup_and_save
from .services.dashboard_stats import build_dashboard_stats
from .services.email_utils import (
    send_assignment_email, send_customer_email, send_fir_approval_email,
    send_remark_updated_email, send_closure_email, send_fir_pdf_email,
)
from .services.latest_update import get_latest_call_update
from .services.report_columns import REPORT_COLUMNS, build_report_row, report_headers
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


# =============================================================================
# Part-A — Manager intake
# =============================================================================
@admin_required(message="New/edit CRSC calls (manager form) is restricted to admin users.")
def manager_form(request, call_id=None):
    entry = get_object_or_404(DirectCall, pk=call_id) if call_id else None
    is_new = entry is None

    if request.method == "POST":
        form = ManagerForm(request.POST, request.FILES, instance=entry, engineer_choices=_engineer_choices())
        if form.is_valid():
            call = form.save(commit=False)
            if is_new:
                call.date_of_complaint = now()
            # Complaint received by is stamped from the authenticated user,
            # not hand-typed.
            call.complaint_received_by = _display_name(request.user)
            previous_assignee = entry.complaint_assigned_to if entry else None
            # Submitted To Email / engineer contact number are looked up
            # from Complaint Assigned To instead of being typed by hand.
            call.submitted_to_email, call.engineer_contact_number = resolve_engineer_contact(
                call.complaint_assigned_to
            )
            # Assigned Date is stamped the first time an engineer is set —
            # feeds the D0 TAT (Assigned - Complaint) calculation.
            if call.complaint_assigned_to and not call.assigned_date:
                call.assigned_date = now()
            compute_tats(call)
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
            _flash_form_errors(request, form)
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
            # Follow-Up Engineer is stamped from the authenticated user, not
            # hand-typed — so the audit trail always names whoever actually
            # made the change.
            updated.follow_up_engineer = _display_name(request.user)

            previous = DirectCall.objects.get(pk=call.pk)
            history_rows = apply_follow_up_rules(updated, previous)
            compute_tats(updated)

            was_fir = previous.call_status == "FIR - For approval"
            updated.save()
            write_history_rows(updated, history_rows)

            if updated.call_status in FIR_CLOSURE_STATUSES and role == "admin":
                recipients = [e for e in [updated.submitted_to_email] if e]
                send_fir_approval_email(updated, recipients)

            # Engineer gets a copy of every new follow-up round they log.
            if any(row["source_field"] == "follow_up" for row in history_rows):
                send_remark_updated_email(updated)

            # Customer is notified again the first time the call reaches
            # one of the "closed out" statuses.
            if (
                updated.call_status != previous.call_status
                and updated.call_status in CUSTOMER_CLOSURE_STATUSES
            ):
                send_closure_email(updated)

            # FIR summary PDF goes to the location handling the device,
            # the first time the call reaches one of the FIR outcomes.
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

    return render(request, "crsc_calls/engineer_form.html", {"form": form, "call": call, "role": role})


# =============================================================================
# Real-Time dashboard
# =============================================================================
PAGE_SIZE = 25


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
    """Parses an HTML5 datetime-local value ('YYYY-MM-DDTHH:MM'); falls back
    to a bare date ('YYYY-MM-DD') for old bookmarked/typed links."""
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


def _apply_filters(request, qs):
    call_status = request.GET.get("call_status")
    call_type = request.GET.get("call_type")
    engineer = request.GET.get("engineer")
    responsibility = request.GET.get("responsibility")
    ialert_ticket_no = request.GET.get("ialert_ticket_no")
    search = (request.GET.get("q") or "").strip()
    bulk_tokens = _parse_bulk_tokens(search)

    if call_status:
        qs = qs.filter(call_status=call_status)
    if call_type:
        qs = qs.filter(call_type=call_type)
    if engineer:
        qs = qs.filter(complaint_assigned_to=engineer)
    if responsibility:
        qs = qs.filter(responsibility=responsibility)
    if ialert_ticket_no:
        qs = qs.filter(ialert_ticket_no__icontains=ialert_ticket_no)

    # Same search box does both a single free-text partial match and a bulk
    # paste of many VIN / PSN / Unique ID values (one per line, or
    # comma/semicolon/whitespace separated) — multiple tokens switch it to
    # an exact, case-insensitive match against all three fields; a single
    # token keeps the more forgiving partial "contains" match.
    if len(bulk_tokens) > 1:
        qs = qs.annotate(
            _uid_u=Upper("unique_id"), _vin_u=Upper("vin"), _psn_u=Upper("psn"),
        ).filter(
            Q(_uid_u__in=bulk_tokens) | Q(_vin_u__in=bulk_tokens) | Q(_psn_u__in=bulk_tokens)
        )
    elif search:
        qs = qs.filter(
            Q(unique_id__icontains=search) | Q(vin__icontains=search) | Q(psn__icontains=search)
        )

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
        rows.append({"call": c, "latest": latest, "cells": build_report_row(c, latest)})

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
        "search": request.GET.get("q", ""),
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


DEFAULT_EXPORT_KEYS = [key for key, _label in REPORT_COLUMNS]


@login_required
def export_page(request):
    """Field-picker screen. Carries the dashboard's current filters forward
    (as hidden inputs) so the export matches whatever's currently on screen."""
    carried = [(k, v) for k, v in request.GET.items() if k not in ("fields",)]
    return render(request, "crsc_calls/export_page.html", {
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

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="crsc_calls_export.csv"'
    writer = csv.writer(response)
    writer.writerow(report_headers(selected_keys))
    for call in qs:
        writer.writerow(build_report_row(call, get_latest_call_update(call), selected_keys))
    return response

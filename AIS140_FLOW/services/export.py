# =============================================================================
# AIS140_FLOW — services/export.py
# Single, field-selectable CSV export. The user checks whichever columns they
# want on the export picker page and downloads just those.
#
# Column set = the mandatory download columns, in their agreed order, plus
# every other field shown on the UI screens (Part-A, Part-B, dashboard and
# the history "eye" view). Anything that appears on no screen is not
# exported.
#
# History-driven columns:
#   * Latest Remarks / Responsibility / Latest Comments / Timestamp carry the
#     ticket's FULL AIS140RequestUpdate history, one event per line, newest
#     first.
#   * D1, D2 ... Dn follow-up groups (Remarks / Comments / Engineer /
#     Closure Timestamp) come from the history rows' `follow_up` number.
#     D1 and D2 are always offered; D3 ... Dn are appended automatically
#     whenever the exported tickets have that many follow-ups.
# =============================================================================
import re

from django.utils.dateformat import format as django_date_format

HISTORY_KEYS = {"history_remarks", "history_comments", "history_responsibility", "history_timestamp"}
FOLLOW_UP_KEY_RE = re.compile(r"^d(\d+)_(remarks|comments|engineer|closure)$")
FOLLOW_UP_PARTS = [
    ("remarks", "Remarks"),
    ("comments", "Comments"),
    ("engineer", "Engineer"),
    ("closure", "Closure Timestamp"),
]
MIN_FOLLOW_UP_GROUPS = 2


def _follow_up_group(n):
    return [(f"d{n}_{part}", f"D{n} {label}", "followup") for part, label in FOLLOW_UP_PARTS]


# (key, column label, kind)
#   kind "field"    -> plain getattr(ticket, key)
#   kind "file"     -> getattr(ticket, key).name if the FileField is set
#   kind "history"  -> built from the full history, see build_history_columns()
#   kind "followup" -> one D<n> value, see build_followup_columns()
#   kind "computed" -> special-cased in build_row()
EXPORT_COLUMNS = (
    [
        ("unique_id", "Unique ID", "field"),
        ("date_of_request", "Date of Request", "field"),
        ("Customer_assigned_date", "Assigned To Engineer Date", "field"),
        ("assigned_engineer_email", "Resp Engineer", "field"),
        ("state", "State", "field"),
        ("request_type", "Request Type", "field"),
        ("vin_no", "Chassis No", "field"),
        ("psn", "PSN No", "field"),
        ("history_remarks", "Latest Remarks", "history"),
        ("history_responsibility", "Responsibility", "history"),
        ("history_comments", "Latest Comments", "history"),
    ]
    + _follow_up_group(1)
    + _follow_up_group(2)
    + [
        ("completion_status", "Completion Status", "field"),
        ("Update_to_AL_API", "Update to A.L", "field"),
        ("completion_date", "Completion Date", "field"),
        ("reupdated_request_al", "Reassigned to DTIL", "field"),
        ("AL_remarks", "Reassigned Remarks", "field"),
        ("AL_comments", "Reassigned Comments", "field"),
        ("engine", "Engine No", "field"),
        ("device_model", "Device Model", "field"),
        ("imei_no", "IMEI No", "field"),
        ("vehicle_no", "Vehicle Regn No", "field"),
        ("vehicle_model", "Vehicle Model", "field"),
        ("customer_name", "Customer Name", "field"),
        ("customer_phone", "Customer Phone No", "field"),
        ("Customer_Alternate_number", "Customer Alternate Phone No", "field"),
        ("Cust_veh_Regn_Address", "Customer Address", "field"),
        ("manufacturing_year", "Manufacturing Year", "field"),
        ("rto_name", "RTO Name", "field"),
        ("rto_code", "RTO Code", "field"),
        ("dealer_name", "Dealer Name", "field"),
        ("Dealer_Contact", "Dealer Contact NO", "field"),
        ("category", "Category", "field"),
        ("remarks", "Remarks", "field"),
        ("ticket_through", "Ticket Through", "field"),
        ("temp_cert_reqd", "Temporary Certificate Required", "field"),
        ("temp_raised_by", "Temporary Certificate Raised By", "field"),
        ("temp_cert_date", "Temporary Certificate Date", "field"),
        ("upload_certificate_in_ialert", "Temporary certificate", "file"),
        ("perm_raised_by", "Permanent Certificate Raised By", "field"),
        ("permanent_cert_date", "Permanent Certificate Date", "field"),
        ("upload_certificate_in_ialert_01", "Permanent certificate", "file"),
        ("upload_certificate_in_ialert_02", "Vahan Certificate", "file"),
        ("D1_TAT", "D1 TAT", "field"),
        ("total_tat", "Total TAT", "field"),
        # ---- other fields shown on the Part-A / Part-B / dashboard screens ----
        ("request_id", "AL Request ID", "field"),
        ("AL_assigned_date", "AL Assigned Date", "field"),
        ("assigned_to", "Assigned To", "field"),
        ("Customer_Email_ID", "Customer Email ID", "field"),
        ("AIS140_Type", "AIS140 Type", "field"),
        ("pan_card", "PAN No", "field"),
        ("aadhar_card", "AADHAR No", "field"),
        ("dealer_code", "Dealer Code", "field"),
        ("Dealer_mail", "Dealer Mail", "field"),
        ("ao_name", "AO Name", "field"),
        ("ro", "RO Name", "field"),
        ("zone", "Zone", "field"),
        ("requested_by", "Requested By", "field"),
        ("requested_name", "Requestor Email ID", "field"),
        ("requested_phone_number", "Requestor Phone Number", "field"),
        ("icicid_no", "ICCID No", "field"),
        ("device_architecture_type", "Device Architecture Type", "field"),
        ("device_battery_voltage", "Device Battery Voltage", "field"),
        ("additional_email_id", "Additional Email ID", "field"),
        ("certification_start_date", "Completion Start Date", "field"),
        ("certification_end_date", "Completion End Date", "field"),
        ("history_timestamp", "Timestamp", "history"),
        ("vahan_format", "Vahan Format", "computed"),
    ]
)

DEFAULT_SELECTED_KEYS = [key for key, _, _ in EXPORT_COLUMNS]  # everything, by default


def _fmt_value(value):
    """Datetimes -> d-m-Y H:i:s, dates -> d-m-Y, None -> ''. Anything else as-is."""
    if value in (None, ""):
        return ""
    if hasattr(value, "hour"):
        return django_date_format(value, "d-m-Y H:i:s")
    if hasattr(value, "year"):
        return django_date_format(value, "d-m-Y")
    return value


def _fmt_dt(value):
    return _fmt_value(value) if value else ""


def max_follow_up_number(tickets_qs):
    """Highest follow-up number (n in D<n>) present in the history of the
    given AIS140Request queryset — used to append D3..Dn columns."""
    from AIS140_FLOW.models import AIS140RequestUpdate

    best = 0
    values = (
        AIS140RequestUpdate.objects
        .filter(ticket__in=tickets_qs, source_field="request_remarks")
        .exclude(follow_up__isnull=True).exclude(follow_up="")
        .values_list("follow_up", flat=True).distinct()
    )
    for value in values:
        m = re.match(r"^D(\d+)$", value or "")
        if m:
            best = max(best, int(m.group(1)))
    return best


def export_columns_for(max_follow_up=0):
    """EXPORT_COLUMNS with D3..D<max_follow_up> groups inserted right after
    the D2 group."""
    if max_follow_up <= MIN_FOLLOW_UP_GROUPS:
        return list(EXPORT_COLUMNS)
    extra = []
    for n in range(MIN_FOLLOW_UP_GROUPS + 1, max_follow_up + 1):
        extra += _follow_up_group(n)
    out = []
    for col in EXPORT_COLUMNS:
        out.append(col)
        if col[0] == f"d{MIN_FOLLOW_UP_GROUPS}_closure":
            out += extra
    return out


def _is_selected(key, selected_keys):
    """D3..Dn columns are generated on the fly, so they follow D2's
    selection rather than being individually listed on the picker page."""
    if key in selected_keys:
        return True
    m = FOLLOW_UP_KEY_RE.match(key)
    return bool(m and int(m.group(1)) > MIN_FOLLOW_UP_GROUPS
                and f"d{MIN_FOLLOW_UP_GROUPS}_{m.group(2)}" in selected_keys)


def build_history_columns(ticket):
    """
    Builds the four 'history' cell values for one ticket: every
    AIS140RequestUpdate row, newest first, one event per line, with the
    remark/comments/responsibility/timestamp lines aligned to each other.
    """
    events = list(ticket.history.all().order_by("-remark_datetime"))
    if not events:
        return {"history_remarks": "", "history_comments": "", "history_responsibility": "", "history_timestamp": ""}

    return {
        "history_remarks": "\n".join(e.latest_remark or "" for e in events),
        "history_comments": "\n".join(e.latest_comments or "" for e in events),
        "history_responsibility": "\n".join(e.responsibility or "" for e in events),
        "history_timestamp": "\n".join(_fmt_dt(e.remark_datetime) for e in events),
    }


def build_followup_columns(ticket):
    """{n: history_row} for every numbered follow-up (D1, D2, ...) on the ticket."""
    out = {}
    for e in ticket.history.filter(source_field="request_remarks").order_by("remark_datetime", "created_at"):
        m = re.match(r"^D(\d+)$", e.follow_up or "")
        if m:
            out[int(m.group(1))] = e
    return out


def _build_vahan_format(ticket):
    """DANL48A|DANL48A032408296045|{ICCID}|{IMEI}|{MM/YYYY}|82

    The month/year is the Vahan date when it has been recorded, otherwise
    the permanent-certificate date, otherwise the completion date.
    """
    if not ticket.icicid_no or not ticket.imei_no:
        return ""
    stamp = ticket.vahan_date or ticket.permanent_cert_date or ticket.completion_date
    if not stamp:
        return ""
    return f"DANL48A|DANL48A032408296045|{ticket.icicid_no}|{ticket.imei_no}|{stamp.strftime('%m/%Y')}|82"


def build_row(ticket, selected_keys, columns=None):
    history_cache = None
    followup_cache = None
    row = []
    for key, _label, kind in (columns or EXPORT_COLUMNS):
        if not _is_selected(key, selected_keys):
            continue
        if kind == "history":
            if history_cache is None:
                history_cache = build_history_columns(ticket)
            row.append(history_cache[key])
        elif kind == "followup":
            if followup_cache is None:
                followup_cache = build_followup_columns(ticket)
            m = FOLLOW_UP_KEY_RE.match(key)
            event = followup_cache.get(int(m.group(1)))
            part = m.group(2)
            if event is None:
                row.append("")
            elif part == "remarks":
                row.append(event.latest_remark or "")
            elif part == "comments":
                row.append(event.latest_comments or "")
            elif part == "engineer":
                row.append(event.attending_engineer or "")
            else:
                row.append(_fmt_dt(event.remark_datetime))
        elif kind == "file":
            f = getattr(ticket, key, None)
            row.append(f.name if f else "")
        elif kind == "computed":
            row.append(_build_vahan_format(ticket) if key == "vahan_format" else "")
        else:
            row.append(_fmt_value(getattr(ticket, key, "")))
    return row


def selected_columns(selected_keys, columns=None):
    return [(key, label) for key, label, _kind in (columns or EXPORT_COLUMNS) if _is_selected(key, selected_keys)]

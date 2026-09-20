# =============================================================================
# AIS140_FLOW — services/export.py
# Single, field-selectable CSV export (replaces the old two-button
# Part-B-CSV / Full-CSV split). The user checks whichever columns they
# want on the export picker page and downloads just those.
#
# The four "history" columns (Latest Remarks / Latest Comments /
# responsibility / Timestamp) are special: instead of only the single
# most-recent event, they contain the ticket's FULL AIS140RequestUpdate
# history, one event per line within the cell, newest first — so a reader
# opening the CSV sees the whole story for that ticket in those four
# columns without needing to open the app.
# =============================================================================
from django.utils.dateformat import format as django_date_format

HISTORY_KEYS = {"history_remarks", "history_comments", "history_responsibility", "history_timestamp"}

# (key, column label, kind)
#   kind "field"   -> plain getattr(ticket, key)
#   kind "file"    -> getattr(ticket, key).name if the FileField is set
#   kind "history" -> built specially, see build_history_columns() below
EXPORT_COLUMNS = [
    ("unique_id", "Unique ID", "field"),
    ("date_of_request", "Date of Request", "field"),
    ("Customer_assigned_date", "Assigned To Engineer Date", "field"),
    ("assigned_engineer_email", "Resp Engineer", "field"),
    ("state", "State", "field"),
    ("request_type", "Request Type", "field"),
    ("vin_no", "Chassis No", "field"),
    ("psn", "PSN No", "field"),
    ("history_remarks", "Latest Remarks", "history"),
    ("history_comments", "Latest Comments", "history"),
    ("history_responsibility", "responsibility", "history"),
    ("history_timestamp", "Timestamp", "history"),
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
    ("certification_start_date", "Completion Start Date", "field"),
    ("certification_end_date", "Completion End Date", "field"),
    ("vahan_date", "Updated in Vahan", "field"),
]

DEFAULT_SELECTED_KEYS = [key for key, _, _ in EXPORT_COLUMNS]  # everything, by default


def _fmt_dt(value):
    if not value:
        return ""
    return django_date_format(value, "d-M-Y H:i")


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


def build_row(ticket, selected_keys):
    """Returns a list of cell values for `ticket`, in the order of `selected_keys`."""
    history_cache = None
    row = []
    for key, _label, kind in EXPORT_COLUMNS:
        if key not in selected_keys:
            continue
        if kind == "history":
            if history_cache is None:
                history_cache = build_history_columns(ticket)
            row.append(history_cache[key])
        elif kind == "file":
            f = getattr(ticket, key, None)
            row.append(f.name if f else "")
        else:
            value = getattr(ticket, key, "")
            row.append(_fmt_dt(value) if key in (
                "date_of_request", "Customer_assigned_date", "completion_date",
                "reupdated_request_al", "temp_cert_date", "permanent_cert_date", "vahan_date",
            ) else (value if value is not None else ""))
    return row


def selected_columns(selected_keys):
    return [(key, label) for key, label, _kind in EXPORT_COLUMNS if key in selected_keys]

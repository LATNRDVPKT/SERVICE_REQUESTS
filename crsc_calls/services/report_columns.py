# =============================================================================
# crsc_calls — services/report_columns.py
# Single source of truth for the CRSC real-time dashboard table AND the CSV
# export — both render exactly these columns, in this order, so the two
# never drift apart.
# =============================================================================
from django.utils.dateformat import format as django_date_format

DATE_FIELDS = {"vehicle_sale_date"}
DATETIME_FIELDS = {
    "date_of_complaint", "assigned_date", "date_of_closure",
    "feedback_submission_datetime", "activation_start_date", "activation_end_date",
    "first_communication_in_darby", "last_communication_in_darby",
}

# (key, column label) — key "latest_update" is special-cased (not a model
# field, comes from services.latest_update.get_latest_call_update()).
REPORT_COLUMNS = [
    ("unique_id", "Unique ID"),
    ("call_type", "Call Type"),
    ("date_of_complaint", "Date of Complaint"),
    ("assigned_date", "Assigned Date"),
    ("complaint_raised_by", "Complaint Raised By"),
    ("complaint_assigned_to", "Assigned To"),
    ("vin", "VIN"),
    ("psn", "PSN"),
    ("call_status", "Call Status"),
    ("date_of_closure", "Closure Date"),
    ("d1_tat", "D0 TAT"),
    ("d2_tat", "D1 TAT"),
    ("total_tat", "Overall TAT"),
    ("ialert_ticket_no", "I Alert Ticket No"),
    ("final_action_taken", "Final Action Taken"),
    ("latest_update", "Latest Update"),
    ("responsibility", "Responsibility"),
    ("hod_comment", "HOD Comments"),
    ("rating", "Rating"),
    ("customer_feedback", "Customer Feedback"),
    ("feedback_submission_datetime", "Feedback submission datetime"),
    ("contact_number", "Contact Number"),
    ("engineer_recommendation", "Engineer Recommendation"),
    ("vehicle_avl_in_workshop", "Vehicle Available in Workshop"),
    ("complaint_raised_from_location", "Complaint Raised Location"),
    ("customer_raised_issue", "Customer Voice"),
    ("complaint_raised", "Complaint Raised"),
    ("customer_mail_id", "Customer Mail ID"),
    ("complaint_raised_through", "Complaint Raised Through"),
    ("complaint_received_by", "Complaint Received By"),
    ("device_model", "Device Model"),
    ("telco_status", "Telco Status"),
    ("active_profile", "Active Profile"),
    ("activation_start_date", "Activation Start Date"),
    ("activation_end_date", "Activation End Date"),
    ("vehicle_sale_date", "Vehicle Sale Date"),
    ("first_communication_in_darby", "First Communication in Darby"),
    ("last_communication_in_darby", "Last Communication in Darby"),
    ("vehicle_type", "Vehicle Type"),
    ("vehicle_run_kilometers", "Vehicle Run"),
    ("main_battery_voltage", "Main Battery Voltage"),
    ("engine_type", "Engine Type"),
    ("vehicle_running_location", "Vehicle Running Location"),
    ("state", "State"),
    ("region", "Region"),
    ("contact_person_name", "Contact Person Name"),
    ("contact_person_number", "Contact Person Number"),
    ("exist_software", "Existing Software"),
    ("updated_software", "Updated Software"),
    ("issue_identified", "Issue Identified"),
    ("issue_description", "Issue Description"),
    ("issue_analysis", "Issue Analysis"),
    ("issue_category", "Issue Category"),
    ("finalised_issue_category", "Finalised Issue Category"),
]


def _fmt_dt(value):
    if not value:
        return ""
    return django_date_format(value, "d-m-Y H:i:s")


def _cell_value(call, key, latest):
    if key == "latest_update":
        return _fmt_dt(latest.get("updated_at")) if latest else ""
    value = getattr(call, key, None)
    if key in DATETIME_FIELDS:
        return _fmt_dt(value)
    if key in DATE_FIELDS:
        return django_date_format(value, "d-m-Y") if value else ""
    return value if value is not None else ""


def build_report_row(call, latest, selected_keys=None):
    """Returns cell values in REPORT_COLUMNS order (includes unique_id).
    `selected_keys` (optional) restricts the row to just those columns —
    used by the CSV field-picker export; the dashboard table always passes
    None to get every column."""
    return [
        _cell_value(call, key, latest)
        for key, _label in REPORT_COLUMNS
        if selected_keys is None or key in selected_keys
    ]


def report_headers(selected_keys=None):
    return [label for key, label in REPORT_COLUMNS if selected_keys is None or key in selected_keys]


def selected_columns(selected_keys):
    return [(key, label) for key, label in REPORT_COLUMNS if key in selected_keys]

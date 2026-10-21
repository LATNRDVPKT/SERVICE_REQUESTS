# =============================================================================
# customer_requests — services/report_columns.py
# Single source of truth for the CRSC real-time dashboard table AND the CSV
# export — both render exactly these columns, in this order, so the two
# never drift apart.
# =============================================================================
import re

from django.utils.dateformat import format as django_date_format

DATE_FIELDS = {"vehicle_sale_date", "device_shipped_date", "faulty_device_shipped_date",
                "faulty_device_reached_date", "commercial_expiry_date"}
DATETIME_FIELDS = {
    "date_of_complaint", "request_received_timestamp", "date_of_closure",
    "activation_start_date", "activation_end_date",
    "first_communication_in_darby", "last_communication_in_darby",
    "S_trigger_date", "s_trigger_completion_date", "C_trigger_date", "c_trigger_completion_date",
    "next_follow_up_exp_date", "feedback_submission_datetime",
}

FOLLOW_UP_KEY_RE = re.compile(r"^d([123])_(remark|comment|exp|closure|engineer)$")


def _follow_up_group(n):
    # follow_up_level never advances past D3, so D1..D3 is the full set.
    return [
        (f"d{n}_remark", f"D{n} Remark"),
        (f"d{n}_comment", f"D{n} Comment"),
        (f"d{n}_exp", f"D{n} Exp Date"),
        (f"d{n}_closure", f"D{n} Closure Date"),
        (f"d{n}_engineer", f"D{n} Engineer"),
    ]


# (key, column label) - "latest_update" and the d<n>_* keys are special-cased
# (not model fields; they come from services.latest_update and the call's
# DirectCallUpdate history).
#
# Order and wording follow the agreed download layout. Only fields that exist
# on the Part-A form, Part-B form or history page are offered; the layout's
# retired columns (region, contact person, HOD comment, payment status ...)
# are not part of the model any more.
REPORT_COLUMNS = (
    [
        ("unique_id", "Unique ID"),
        ("date_of_complaint", "Date of Complaint"),
        ("request_received_timestamp", "Request Recd Timestamp"),

        ("call_type", "Call Type"),
        ("vin", "VIN"),
        ("psn", "PSN"),
        ("complaint_assigned_to", "Complaint Assigned To"),
        ("call_status", "Call Status"),
        ("responsibility", "Responsibility"),

        ("date_of_closure", "Date of Closure"),
        ("rr_responsibility", "RR Responsibility"),

        ("ialert_ticket_no", "Ticket No"),
        ("rating", "Rating"),
        ("customer_confirmation", "Confirmation"),
        ("complaint_raised_from_location", "Complaint Raised From Location"),
        ("customer_raised_issue", "Customer Raised Issue"),
        ("complaint_raised", "Complaint Raised"),
        ("complaint_raised_by", "Complaint Raised By"),
        ("contact_number", "Contact Number"),
        ("customer_mail_id", "Customer Mail ID"),
        ("vehicle_avl_in_workshop", "Vehicle Avl in Workshop"),
        ("complaint_raised_through", "Complaint Raised Through"),
        ("complaint_received_by", "Complaint Received By"),
        ("submitted_to_email", "Submitted To Email"),
        ("engineer_contact_number", "Engineer Contact Number"),
        ("end_customer_mail_id", "End Customer Mail ID"),
        ("device_model", "Device Model"),
        ("telco_status", "Telco Status"),
        ("active_profile", "Active Profile"),
        ("activation_start_date", "Activation Start Date"),
        ("activation_end_date", "Activation End Date"),
        ("vehicle_sale_date", "Vehicle Sale Date"),
        ("first_communication_in_darby", "First Communication in Darby"),
        ("last_communication_in_darby", "Last Communication in Darby"),
        ("card_status", "Card Status"),
        ("main_battery_voltage", "Main Battery Voltage"),
        ("exist_software", "Exist Software"),
        ("al_mfg_plant", "AL Mfg Plant"),
        ("nrd_category", "NRD Category"),
        ("vehicle_type", "Vehicle Type"),
        ("engine_type", "Engine Type"),
        ("state", "State"),
        ("kilometers_hours", "Kilometers Hours"),
        ("vehicle_running_location", "Vehicle Running Location"),
        ("updated_software", "Updated Software"),
        ("issue_identified", "Issue Identified"),
        ("issue_analysis", "Issue Analysis"),
        ("follow_up_remark", "Latest Remark"),
        ("follow_up_comment", "Latest Comment"),
        ("follow_up_level", "Latest Follow-up Level"),
        ("follow_up_engineer", "LatestEngineer Name"),
        ("next_follow_up_exp_date", "Exp Review Date"),
        ("latest_update", "Latest Update Timestamp"),        
    ]
    + _follow_up_group(1)
    + _follow_up_group(2)
    + _follow_up_group(3)
    + [

        ("engineer_recommendation", "Engineer Recommendation"),
        ("upload_file_01", "Analysis"),
        ("chargable_or_not", "Chargeable or Not"),
        ("remarks", "Remarks"),
        ("external_modification", "External Modification"),
        ("device_IMEI", "Device IMEI"),
        ("device_ICCID", "Device ICCID"),
        ("device_to_be_sent", "Device to be Sent"),
        ("dealer_address", "Dealer Address"),
        ("dealer_name", "Dealer Name"),
        ("customer_satisfaction", "Feedback"),
        ("customer_feedback", "Customer Feedback"),
        ("feedback_submission_datetime", "Feedback Submitted Datetime"),
        ("Latency_7_days", "Latency for Last 7 Days CC"),
        ("V_packet_7_days", "VPacket for Last 7 Days CC"),
        # ---- remaining Part-A / Part-B / history fields not in the layout ----
        ("Latency_3_months", "Latency for Last 3 Months"),
        ("V_packet_3_months", "VPacket for Last 3 Months"),
        ("veh_reg_no", "Vehicle Regn No"),
        ("veh_model", "Vehicle Model"),
        ("upload_file", "Upload File"),
        ("al_updated_contact_no", "Updated Contact No"),

        ("S_trigger_date", "S Trigger Date"),
        ("s_trigger_completion_date", "S Trigger Completion Date"),
        ("C_trigger_date", "C Trigger Date"),
        ("c_trigger_completion_date", "C Trigger Completion Date"),
        ("payment_status", "Payment Status"),
        ("hod_comment", "HOD Comment"),
        # ---- faulty-device logistics / replacement follow-through ----
        ("faulty_device_shipped_date", "Faulty Device Shipped Date"),
        ("faulty_device_shipped_thru", "Faulty Device Shipped Thru"),
        ("faulty_device_shipped_lr_details", "Faulty Device Shipped LR Details"),
        ("faulty_device_reached_date", "Faulty Device Reached Date"),
        ("faulty_device_confirmation", "Faulty Device Confirmation from Plant"),
        ("new_device_serial_no", "Repaired/New Device Serial No"),
        ("validity_transfer_completed", "Validity Transfer Completed"),
        ("mapping_completed", "Mapping Completed"),
        ("commercial_expiry_date", "Commercial Expiry Date"),
        ("new_device_fitted_in_vehicle", "Repaired/New Device Fitted in Vehicle"),
        ("new_device_working", "Repaired/New Device Working"),
        # ---- plant update ----
        ("plant_status", "Plant Status"),
        ("copq_labour", "CoPQ Labour"),
        ("copq_material", "CoPQ Material"),
        ("materials_used", "Materials Used"),
        ("plant_analysis", "Plant Analysis"),
        ("plant_conclusion", "Plant Conclusion"),
        ("device_shipped_date", "Device Shipped Date"),
        ("device_shipped_through", "Device Shipped Through"),
        ("device_shipped_lr_no", "Device Shipped LR No"),
    ]
)


# Columns ticked by default on the export picker (and used when a download is
# requested with nothing ticked). Everything else in REPORT_COLUMNS can still
# be ticked on the page.
DEFAULT_EXPORT_KEYS = [
    "unique_id", "date_of_complaint", "call_type",
    "vin", "psn", "complaint_assigned_to",
    "call_status", "date_of_closure", "ialert_ticket_no",
    "request_received_timestamp", "ialert_remarks", "complaint_raised_from_location",
    "customer_raised_issue", "complaint_raised", "complaint_raised_by",
    "contact_number", "customer_mail_id", "vehicle_avl_in_workshop",
    "complaint_raised_through", "end_customer_mail_id", "device_model",
    "telco_status", "active_profile", "activation_start_date",
    "activation_end_date", "vehicle_sale_date", "first_communication_in_darby",
    "last_communication_in_darby", "card_status", "main_battery_voltage",
    "exist_software", "al_mfg_plant", "nrd_category",
    "vehicle_type", "engine_type", "state",
    "kilometers_hours", "vehicle_running_location", "updated_software",
    "issue_identified", "issue_analysis", "engineer_recommendation",
    "upload_file_01", "chargable_or_not", "remarks",
    "external_modification", "device_IMEI", "device_ICCID",
    "device_to_be_sent", "dealer_address", "dealer_name",
    "follow_up_engineer", "Latency_7_days", "V_packet_7_days",
    "Latency_3_months", "V_packet_3_months", "veh_reg_no",
    "veh_model", "upload_file", "al_updated_contact_no",
    "follow_up_remark", "follow_up_comment", "follow_up_level",
    "responsibility", "S_trigger_date", "s_trigger_completion_date",
    "C_trigger_date", "c_trigger_completion_date", "hod_comment",
]


def _fmt_dt(value):
    if not value:
        return ""
    return django_date_format(value, "d-m-Y H:i:s")


def _follow_up_events(call):
    """{n: DirectCallUpdate} - the most recent follow-up event for D1, D2 and D3."""
    cache = getattr(call, "_follow_up_cache", None)
    if cache is None:
        cache = {}
        events = call.history.filter(source_field="follow_up").order_by("event_datetime", "created_at")
        for e in events:  # ascending, so later rows overwrite earlier ones
            m = re.match(r"^D([123])$", e.follow_up_level or "")
            if m:
                cache[int(m.group(1))] = e
        call._follow_up_cache = cache
    return cache


def _cell_value(call, key, latest):
    if key == "latest_update":
        return _fmt_dt(latest.get("updated_at")) if latest else ""
    m = FOLLOW_UP_KEY_RE.match(key)
    if m:
        event = _follow_up_events(call).get(int(m.group(1)))
        if event is None:
            return ""
        part = m.group(2)
        if part == "remark":
            return event.remark or ""
        if part == "comment":
            return event.comment or ""
        if part == "exp":
            return _fmt_dt(event.next_follow_up_exp_date)
        if part == "closure":
            return _fmt_dt(event.event_datetime)
        return event.engineer or ""
    value = getattr(call, key, None)
    if key in DATETIME_FIELDS:
        return _fmt_dt(value)
    if key in DATE_FIELDS:
        return django_date_format(value, "d-m-Y") if value else ""
    if hasattr(value, "name") and hasattr(value, "storage"):  # FileField
        return value.name or ""
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

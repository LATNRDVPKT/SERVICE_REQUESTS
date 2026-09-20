# =============================================================================
# crsc_calls — services/export.py
# Full-record CSV export. The original download_csv only exported a narrow
# FIR-focused column set; this covers every Part-A/Part-B/follow-up field
# so nothing is silently missing from the report.
# =============================================================================
from django.utils.dateformat import format as django_date_format

EXPORT_COLUMNS = [
    ("unique_id", "Unique ID"), ("date_of_complaint", "Date of Complaint"),
    ("vin", "VIN"), ("psn", "PSN"), ("veh_reg_no", "Vehicle Regn No"),
    ("complaint_raised_by", "Complaint Raised By"), ("complaint_raised", "Complaint Raised"),
    ("complaint_raised_from_location", "Complaint Location"),
    ("customer_raised_issue", "Customer Voice"),
    ("contact_number", "Contact Number"), ("customer_mail_id", "Customer Mail ID"),
    ("complaint_assigned_to", "Engineer Responsible"), ("submitted_to_email", "Submitted To Email"),
    ("call_type", "Call Type"), ("ialert_ticket_no", "iAlert Ticket No"),
    ("state", "State"), ("region", "Region"), ("dealer_name", "Dealer Name"),
    ("device_model", "Device Model"), ("veh_model", "Vehicle Model"),
    ("call_status", "Call Status"), ("date_of_closure", "Date of Closure"),
    ("follow_up_level", "Follow-Up Level"), ("follow_up_remark", "Follow-Up Remark"),
    ("follow_up_comment", "Follow-Up Comment"), ("follow_up_engineer", "Follow-Up Engineer"),
    ("follow_up_closure_date", "Follow-Up Closure Date"),
    ("next_follow_up_exp_date", "Next Follow-Up Expected Date"),
    ("al_updated_contact_no", "AL Updated Contact No"),
    ("issue_identified", "Issue Identified"), ("issue_analysis", "Issue Analysis"),
    ("final_analysis", "Final Analysis"), ("finalised_issue_category", "Finalised Issue Category"),
    ("engineer_recommendation", "Engineer Recommendation"), ("hod_comment", "HOD Comment"),
    ("chargable_or_not", "Chargeable or Not"), ("payment_status", "Payment Status"),
    ("remarks", "Remarks"),
    ("external_modification", "External Modification"), ("device_IMEI", "Device IMEI"),
    ("device_ICCID", "Device ICCID"), ("device_to_be_sent", "Device to be Sent"),
    ("dealer_address", "Dealer Address"),
    ("d1_tat", "D1 TAT"), ("d2_tat", "D2 TAT"), ("total_tat", "Total TAT"),
]


def _fmt(value, key):
    if key in ("date_of_complaint", "date_of_closure", "follow_up_closure_date", "next_follow_up_exp_date"):
        return django_date_format(value, "d-M-Y H:i") if value else ""
    return value if value is not None else ""


def build_row(call):
    return [_fmt(getattr(call, key, ""), key) for key, _label in EXPORT_COLUMNS]


def export_headers():
    return [label for _key, label in EXPORT_COLUMNS]

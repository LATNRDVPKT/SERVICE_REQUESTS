# =============================================================================
# AIS140_FLOW — constants.py
# Central place for business-rule lookup tables shared across views/services.
# =============================================================================

# Completion statuses that close a ticket (read-only in Part-B once reached,
# and trigger the completion e-mail + completion_date auto-stamp).
TERMINAL_STATUSES = frozenset([
    "Permanent",
    "Temp + Perm",
    "Cancelled",
    "Reject",
    "Third Party Device-Rejected",
])

# Statuses that also count as "terminal" purely for auto-stamping completion_date.
COMPLETION_DATE_TRIGGER_STATUSES = frozenset([
    "Temporary", "Permanent", "Cancelled", "Third Party Device-Rejected",
])

# ---------------------------------------------------------------------------
# REQ-08 — Latest Remark -> Responsibility mapping
# ---------------------------------------------------------------------------
RESPONSIBILITY_MAP = {
    "SIM VALIDITY NOT OK": "AL",
    "VEHICLE REPORT TO WS": "DTIL",
    "CUSTOMER NOT ANSWERING": "DEALER/CUSTOMER",
    "TP- DEVICE TO UNTAG": "DEALER/CUSTOMER",
    "SOS NOT FITTED TO CANCEL": "DEALER/CUSTOMER",
    "MISMAPPING": "AL",
    "VEH IN BODY BUILDING": "DEALER/CUSTOMER",
    "SERVER ISSUE": "STU",
    "CONTACT DETAIL WRONG": "DEALER/CUSTOMER",
    "VEHICLE OUT OF STATE": "DEALER/CUSTOMER",
    "SOS NOT WORKING": "DEALER/CUSTOMER",
    "OTHERS": "DEALER/CUSTOMER",
    "CUSTOMER SUPPORT PENDING": "DEALER/CUSTOMER",
    "DEVICE GETTING NOT POWERING ON": "DEALER/CUSTOMER",
    "REG NO AND DATE REQUIRED": "AL",
    "AIS140 CERTIFICATE READY - CONFIRM VEHICLE VISIT DATE TO RTO": "DEALER/CUSTOMER",
    "NECESSARY SUPPORT PROVIDED": "DTIL",
}


def get_responsibility(remark):
    """Case-insensitive lookup into RESPONSIBILITY_MAP. Returns '' if unknown."""
    if not remark:
        return ""
    return RESPONSIBILITY_MAP.get(str(remark).strip().upper(), "")


# ---------------------------------------------------------------------------
# Request remarks — selectable options + auto-mapped default comment text.
# The dropdown in Part-B is built from RESPONSIBILITY_MAP's keys (same list
# used for the AL responsibility lookup), so every remark an engineer can
# pick always resolves to a responsibility. REMARK_COMMENT_MAP supplies a
# sensible starting comment for each remark — the engineer can still edit
# it; JS only fills the box if it's still empty (see static/js/app.js).
# ---------------------------------------------------------------------------
REQUEST_REMARK_CHOICES = [("", "Please Select")] + [(k, k) for k in RESPONSIBILITY_MAP.keys()]

REMARK_COMMENT_MAP = {
    "SIM VALIDITY NOT OK": "SIM validity has expired or is invalid — renewal/replacement requested.",
    "VEHICLE REPORT TO WS": "Vehicle has been asked to report to the workshop.",
    "CUSTOMER NOT ANSWERING": "Customer is not answering calls; follow-up will be retried.",
    "TP- DEVICE TO UNTAG": "Third-party device needs to be untagged from the account.",
    "SOS NOT FITTED TO CANCEL": "SOS is not fitted; requesting cancellation of the requirement.",
    "MISMAPPING": "Vehicle mapping mismatch identified; correction requested with AL.",
    "VEH IN BODY BUILDING": "Vehicle is currently with the body builder.",
    "SERVER ISSUE": "Server-side issue observed; monitoring until resolved.",
    "CONTACT DETAIL WRONG": "Contact details on file appear to be incorrect.",
    "VEHICLE OUT OF STATE": "Vehicle is currently outside the serviceable state.",
    "SOS NOT WORKING": "SOS button is not functioning as expected.",
    "OTHERS": "See remarks for details.",
    "CUSTOMER SUPPORT PENDING": "Customer support call is pending.",
    "DEVICE GETTING NOT POWERING ON": "Device is not powering on.",
    "REG NO AND DATE REQUIRED": "Registration number and date required from the customer/dealer.",
    "AIS140 CERTIFICATE READY - CONFIRM VEHICLE VISIT DATE TO RTO":
        "Certificate is ready — confirm the vehicle's visit date to the RTO.",
    "NECESSARY SUPPORT PROVIDED": "Necessary support has been provided to resolve the issue.",
}

CERTIFICATE_EVENT_REMARKS = {
    "permanent_certificate": "Permanent certificate uploaded",
    "temporary_certificate": "Temporary certificate uploaded",
}

# ---------------------------------------------------------------------------
# Update_to_AL_API -> which certificate fields must be attached to the
# outbound iAlert payload (used by services/ialert.py)
# ---------------------------------------------------------------------------
IALERT_FILE_MAPPING = {
    "Temporary": [
        ("upload_certificate_in_ialert", "temp_certificate"),
        ("upload_certificate_in_ialert_01", "vltd_certificate_1"),
    ],
    "Permanent": [
        ("upload_certificate_in_ialert_01", "vltd_certificate_1"),
        ("upload_certificate_in_ialert_02", "vltd_certificate_2"),
    ],
    "Temp + Perm": [
        ("upload_certificate_in_ialert", "temp_certificate"),
        ("upload_certificate_in_ialert_01", "vltd_certificate_1"),
        ("upload_certificate_in_ialert_02", "vltd_certificate_2"),
    ],
}

# ---------------------------------------------------------------------------
# Engineer name -> e-mail lookup used when a Part-A "assigned_to" value is a
# short name rather than a full e-mail address. Fill in your own team here,
# or replace resolve_engineer_email() with a DB-backed lookup.
# ---------------------------------------------------------------------------
ENGINEER_EMAIL_MAP = {
    # "Short Name": "person@yourcompany.com",
}

# Extra CC recipients per state, added to the request-remark and completion e-mails.
STATE_EXTRA_EMAILS = {
    # "KARNATAKA": ["sales.hubli@example.com"],
}

# Additional fixed CC recipients on the Part-A assignment e-mail.
PART_A_ASSIGNMENT_CC = [
    # "manager@yourcompany.com",
]

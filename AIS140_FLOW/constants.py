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

# States where Temporary Certificate Required defaults to "Yes" on new
# tickets (engineers can still change it in Part-B afterward).
TEMP_CERT_DEFAULT_YES_STATES = frozenset([
    "KARNATAKA", "TAMIL NADU", "HIMACHAL PRADESH", "WEST BENGAL",
])

# ---------------------------------------------------------------------------
# REQ-08 — Latest Remark -> Responsibility mapping
# ---------------------------------------------------------------------------
RESPONSIBILITY_MAP = {
    "SIM VALIDITY NOT OK": "AL",
    "VEHICLE REPORT TO WS": "DANLAW",
    "CUSTOMER NOT ANSWERING": "DEALER/CUSTOMER",
    "TP- DEVICE TO UNTAG": "DEALER/CUSTOMER",
    "SOS NOT FITTED TO CANCEL": "DEALER/CUSTOMER",
    "MISMAPPING": "AL",
    "VEH IN BODY BUILDING": "DEALER/CUSTOMER",
    "SERVER ISSUE": "STU",
    "CONTACT DETAILS WRONG": "DEALER/CUSTOMER",
    "VEHICLE OUT OF STATE": "DEALER/CUSTOMER",
    "SOS NOT WORKING": "DEALER/CUSTOMER",
    "OTHERS": "CUSTOMER",
    "CUSTOMER SUPPORT PENDING": "DEALER/CUSTOMER",
    "DEVICE GETTING NOT POWERING ON": "DEALER/CUSTOMER",
    "REG NO AND DATE REQUIRED": "AL",
    "AIS140 CERTIFICATE READY - CONFIRM VEHICLE VISIT DATE TO RTO": "DEALER/CUSTOMER",
    "NECESSARY SUPPORT PROVIDED": "DANLAW",
    "WIRE CUT ALERT": "DEALER/CUSTOMER",
    "TP- FITTED AND TO CANCEL": "DEALER/CUSTOMER",
    "AIS140 REQUEST TO CANCEL": "CUSTOMER",
}

RESPONSIBILITY_CHOICES = [
    ("AL", "AL"),
    ("CUSTOMER", "CUSTOMER"),
    ("DANLAW", "DANLAW"),
    ("DEALER/CUSTOMER", "DEALER/CUSTOMER"),
]


def get_responsibility(source_field, remark):
    """
    Responsibility rule for AIS140:
      - the latest event is an AL Remarks update -> AL ("Action - AL")
      - the latest event is a Reupdated Request AL update -> DANLAW
        ("Action - Danlaw")
      - otherwise, looked up from the remark via RESPONSIBILITY_MAP
        (case-insensitive; unmapped remarks resolve to "")
    """
    if source_field == "al_remarks":
        return "AL"
    if source_field == "reupdated_request_al":
        return "DANLAW"
    if not remark:
        return ""
    return RESPONSIBILITY_MAP.get(str(remark).strip().upper(), "")


# ---------------------------------------------------------------------------
# Request remarks — selectable options + auto-mapped default comment text.
# The dropdown in Part-B is built from REMARK_COMMENT_MAP's keys, so every
# remark an engineer can pick always has a starting comment. The engineer
# can still edit the comment; JS only fills the box if it's still empty
# (see static/js/app.js) — the server applies the same default as a
# fallback for non-JS submissions (see services/workflow.py).
# Responsibility (RESPONSIBILITY_MAP, above) is a separate lookup — a
# remark with no responsibility entry simply resolves to "" via
# get_responsibility(), same as any other unmapped remark.
# ---------------------------------------------------------------------------
REMARK_COMMENT_MAP = {
    "CONTACT DETAILS WRONG":
        "Called given customer no:( ). Wrong contact no. Dealer to provide correct No",
    "CUSTOMER NOT ANSWERING":
        "Called given number ( ). Not answering, Please provide alternative number and ask customer to call us for to complete certfication",
    "CUSTOMER SUPPORT PENDING":
        "Called given number ( ). Not answering, Please provide alternative number and ask customer to call us for to complete certfication",
    "SOS NOT FITTED TO CANCEL":
        "Verified in the vehicle and found NO SOS switch fitted. Customer /AL to re assign / call ( )",
    "SOS NOT WORKING":
        "Verified and found SOS alert not Getting pushed. Please check SOS wiring. Customer /AL to re assign / call ( )",
    "WIRE CUT ALERT":
        "Verified in the vehicle and found Wire cut / Tamper alert being recd in STU server. Pl check SOS wiring. Customer /AL to re assign / call ( )",
    "VEH IN BODY BUILDING":
        "Verified and found vehicle in Body Building. Customer /AL to re assign / call ( ) once Body building is completed and Vehicle in LIVE status with ignition ON.",
    "TP- DEVICE TO UNTAG":
        "Verified and found Third party device fitted / Device SL. No. updated in Vahan portal. Request customer to remove the device / take up with the third party vendor and ask him to untag his device from Vahan portal. Pl call once done",
    "DEVICE GETTING NOT POWERING ON":
        "Device not getting power from Vehicle end. Please check with dealer for Main battery disconnected, proper Fuse fitment / Wiring connection and powering on to the device. Call back once Powering issue is resolved to ( )",
    "SIM VALIDITY NOT OK":
        "Found the vehicle SIM subscription is not meeting the requirement of certification, AL to update and reassign",
    "VEHICLE REPORT TO WS":
        "AIS140 SW Config. Not getting success in FOTA(Network issue, SIM not latching with N/W), Vehicle report to WS for manual SW Update/Replacement",
    "TP- FITTED AND TO CANCEL":
        "As per govt sever vehicle found tagged with Third party device fitted, Request customer to take up with Third party and remove the device / tagging from Govt server.",
    "MISMAPPING":
        "Vehicle  found, fitted with wrong PSN(Device), To check with body builder and correct it.",
    "VEHICLE OUT OF STATE":
        "Vehicle is  not running  in  Requested  Registration  state. Customer to call/Message/Mail once vehicle returns to state of Registration proposed.",
    "SERVER ISSUE":
        "1) STU Server not working,         2) Govt stopped certification for already registered vehicles          3) No STU approval for specific state.",
    "REG NO AND DATE REQUIRED":
        "Since Vehicle is already registered please provide registration no and date to proceed activation. Update in AL portal/Send mail with details.",
    "OTHERS":
        "1) Vehicle not in proper network area          2)Device missing ",
    "AIS140 certificate ready - Confirm vehicle visit date to RTO":
        "D2- Dealer to ensure vehicle running for 50 Kms minimum after RTO approval failing with penalty of 1L applicable for dealer/Customer",
    "AIS140 request to cancel": "",
}

REQUEST_REMARK_CHOICES = [("", "Please Select")] + [(k, k) for k in REMARK_COMMENT_MAP.keys()]

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

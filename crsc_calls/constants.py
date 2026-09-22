# =============================================================================
# crsc_calls — constants.py
# =============================================================================

# Remarks available to every call, plus four extra remarks only offered for
# direct_call (not iAlert calls) — SIM EXPIRED, DEVICE TO BE SENT FOR
# REPAIR/REPLACE, CANCELLED.
COMMON_REMARKS = [
    "CONTACT DETAILS WRONG",
    "CUSTOMER ISSUE - DASHBOARD MODIFICATION",
    "CUSTOMER ISSUE - FUSE",
    "CUSTOMER ISSUE - PHYSICAL DAMAGE",
    "CUSTOMER ISSUE - THIRDPARTY DEVICE",
    "CUSTOMER ISSUE - VEHICLE WIRING",
    "CUSTOMER ISSUE - WATER INGRESS",
    "CUSTOMER NOT ANSWERING",
    "CUSTOMER RESCHEDULING - VEHICLE SUPPORT DATE",
    "DEALER SENT DEVICE FOR SERVICE",
    "DEVICE DISPATCHED TO WORKSHOP",
    "iALERT ISSUE",
    "ISSUE RESOLVED",
    "MONITORING",
    "NO ISSUE - CUSTOMER COMPLAINT",
    "OUT OF WARRANTY",
    "VEHICLE PHYSICAL SUPPORT - WAITING",
    "VIDEO CALL SUPPORT - WAITING",
]

DIRECT_CALL_ONLY_REMARKS = [
    "SIM EXPIRED",
    "DEVICE TO BE SENT FOR REPAIR",
    "DEVICE TO BE SENT FOR REPLACE",
    "CANCELLED",
]

ALL_REMARKS = COMMON_REMARKS + DIRECT_CALL_ONLY_REMARKS


def remark_choices_for(call_type):
    """direct_call gets the 4 extra remarks; every other call_type gets COMMON_REMARKS only."""
    remarks = ALL_REMARKS if call_type == "direct_call" else COMMON_REMARKS
    return [("", "Please Select")] + [(r, r) for r in remarks]


# Suggested default comment per remark — auto-fills follow_up_comment (only
# when it's still empty), same UX as AIS140's request_remarks autofill.
REMARK_COMMENT_MAP = {
    "CONTACT DETAILS WRONG": "Contact details on file appear to be incorrect.",
    "CUSTOMER ISSUE - DASHBOARD MODIFICATION": "Customer has modified the dashboard/wiring near the device.",
    "CUSTOMER ISSUE - FUSE": "Issue traced to a blown/faulty fuse.",
    "CUSTOMER ISSUE - PHYSICAL DAMAGE": "Physical damage observed on the device/harness.",
    "CUSTOMER ISSUE - THIRDPARTY DEVICE": "A third-party device is interfering with normal operation.",
    "CUSTOMER ISSUE - VEHICLE WIRING": "Vehicle wiring issue identified as the root cause.",
    "CUSTOMER ISSUE - WATER INGRESS": "Water ingress observed in the device/connector.",
    "CUSTOMER NOT ANSWERING": "Customer is not answering calls; follow-up will be retried.",
    "CUSTOMER RESCHEDULING - VEHICLE SUPPORT DATE": "Customer has asked to reschedule the vehicle support visit.",
    "DEALER SENT DEVICE FOR SERVICE": "Dealer has sent the device for service.",
    "DEVICE DISPATCHED TO WORKSHOP": "Device has been dispatched to the workshop.",
    "iALERT ISSUE": "Issue originates on the iAlert platform side.",
    "ISSUE RESOLVED": "Issue has been resolved.",
    "MONITORING": "Case is under monitoring; no action needed right now.",
    "NO ISSUE - CUSTOMER COMPLAINT": "No technical issue found; customer complaint only.",
    "OUT OF WARRANTY": "Device/vehicle is out of warranty.",
    "VEHICLE PHYSICAL SUPPORT - WAITING": "Waiting on vehicle physical support visit.",
    "VIDEO CALL SUPPORT - WAITING": "Waiting on a scheduled video-call support session.",
    "SIM EXPIRED": "SIM has expired; renewal requested.",
    "DEVICE TO BE SENT FOR REPAIR": "Device needs to be sent in for repair.",
    "DEVICE TO BE SENT FOR REPLACE": "Device needs to be sent in for replacement.",
    "CANCELLED": "Call has been cancelled.",
}


# ---------------------------------------------------------------------------
# Latest Remark -> Responsibility mapping. Every remark in ALL_REMARKS is
# covered, so any call with a follow-up remark always has a responsibility.
# ---------------------------------------------------------------------------
RESPONSIBILITY_MAP = {
    "CONTACT DETAILS WRONG": "AL",
    "CUSTOMER ISSUE - DASHBOARD MODIFICATION": "CUSTOMER",
    "CUSTOMER ISSUE - FUSE": "CUSTOMER",
    "CUSTOMER ISSUE - PHYSICAL DAMAGE": "CUSTOMER",
    "CUSTOMER ISSUE - THIRDPARTY DEVICE": "CUSTOMER",
    "CUSTOMER ISSUE - VEHICLE WIRING": "CUSTOMER",
    "CUSTOMER ISSUE - WATER INGRESS": "AL",
    "CUSTOMER NOT ANSWERING": "AL",
    "CUSTOMER RESCHEDULING - VEHICLE SUPPORT DATE": "CUSTOMER",
    "DEALER SENT DEVICE FOR SERVICE": "DANLAW",
    "DEVICE DISPATCHED TO WORKSHOP": "DANLAW",
    "iALERT ISSUE": "AL",
    "ISSUE RESOLVED": "CLOSED",
    "MONITORING": "DANLAW",
    "NO ISSUE - CUSTOMER COMPLAINT": "AL",
    "OUT OF WARRANTY": "CUSTOMER",
    "VEHICLE PHYSICAL SUPPORT - WAITING": "CUSTOMER",
    "VIDEO CALL SUPPORT - WAITING": "CUSTOMER",
    "SIM EXPIRED": "CUSTOMER",
    "DEVICE TO BE SENT FOR REPAIR": "DANLAW",
    "DEVICE TO BE SENT FOR REPLACE": "DANLAW",
    "CANCELLED": "CUSTOMER",
}

RESPONSIBILITY_CHOICES = [
    ("DANLAW", "DANLAW"),
    ("CUSTOMER", "CUSTOMER"),
    ("AL", "AL"),
    ("CLOSED", "CLOSED"),
]


def get_responsibility(source_field, remark):
    """
    Responsibility rule for CRSC Calls:
      - the latest event is an AL-updated-contact-number event -> DANLAW
      - otherwise, looked up from the remark via RESPONSIBILITY_MAP
        (case-insensitive; every selectable remark is covered)
    """
    if source_field == "al_updated_contact_no":
        return "DANLAW"
    return RESPONSIBILITY_MAP.get((remark or "").strip().upper(), "")


def format_update_to_al(follow_up_level, remark):
    """'D1 - iALERT ISSUE' style string sent to the AL API."""
    if not follow_up_level or not remark:
        return ""
    return f"{follow_up_level} - {remark}"


# ---------------------------------------------------------------------------
# E-mail CC lists — fill in for your own team. Left empty by default.
# ---------------------------------------------------------------------------
CRSC_ASSIGNMENT_CC = [
    # "sales@yourcompany.com",
]
CRSC_CUSTOMER_CC = [
    # "sales@yourcompany.com",
]

# ---------------------------------------------------------------------------
# Complaint Assigned To -> engineer contact details. Replaces the old manual
# "Submitted To Email" / "Complaint Assigned Contact Number" form fields —
# the manager form now looks the assignee up here instead. Dummy placeholder
# values until real ones are supplied.
# ---------------------------------------------------------------------------
ENGINEER_CONTACT_MAP = {
    "Engineer One": {"email": "engineer1@dummy-crsc.local", "phone": "9000000001"},
    "Engineer Two": {"email": "engineer2@dummy-crsc.local", "phone": "9000000002"},
    "Engineer Three": {"email": "engineer3@dummy-crsc.local", "phone": "9000000003"},
    "Engineer Four": {"email": "engineer4@dummy-crsc.local", "phone": "9000000004"},
    "Engineer Five": {"email": "engineer5@dummy-crsc.local", "phone": "9000000005"},
    "Engineer Six": {"email": "engineer6@dummy-crsc.local", "phone": "9000000006"},
    "Engineer Seven": {"email": "engineer7@dummy-crsc.local", "phone": "9000000007"},
    "Engineer Eight": {"email": "engineer8@dummy-crsc.local", "phone": "9000000008"},
    "Engineer Nine": {"email": "engineer9@dummy-crsc.local", "phone": "9000000009"},
    "Engineer Ten": {"email": "engineer10@dummy-crsc.local", "phone": "9000000010"},
    "Engineer Eleven": {"email": "engineer11@dummy-crsc.local", "phone": "9000000011"},
}


def resolve_engineer_contact(assigned_to):
    """Returns (email, phone) for a Complaint Assigned To value. Falls back
    to a deterministic dummy address/number for any name not in the map
    (e.g. a future engineer added via seed_users) so the lookup never blocks
    saving the call."""
    entry = ENGINEER_CONTACT_MAP.get(assigned_to)
    if entry:
        return entry["email"], entry["phone"]
    if not assigned_to or assigned_to == "others":
        return "", ""
    slug = "".join(ch if ch.isalnum() else "." for ch in assigned_to.strip().lower()).strip(".")
    return f"{slug}@dummy-crsc.local", "9000000000"


# ---------------------------------------------------------------------------
# Device to be Sent (location) -> FIR PDF recipient. REPLACE THESE with the
# real addresses for each location — dummy placeholders until then, same
# convention as ENGINEER_CONTACT_MAP above.
# ---------------------------------------------------------------------------
DEVICE_LOCATION_EMAIL_MAP = {
    "Goa": "goa-fir@dummy-crsc.local",
    "Hyderabad": "hyderabad-fir@dummy-crsc.local",
    "Chennai": "chennai-fir@dummy-crsc.local",
}


def resolve_fir_pdf_recipient(device_to_be_sent):
    """Returns the FIR-PDF recipient e-mail for a Device to be Sent
    location, or "" if the location isn't set/known."""
    return DEVICE_LOCATION_EMAIL_MAP.get(device_to_be_sent, "")

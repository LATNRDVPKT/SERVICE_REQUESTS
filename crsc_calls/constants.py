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


def get_responsibility(source_field, remark):
    """
    REQ-style responsibility rule specified for CRSC Calls:
      - the latest event is an AL-updated-contact-number event -> DANLAW
      - the latest event's remark is "iALERT ISSUE"              -> AL
      - anything else                                            -> FOLLOW-UP
    """
    if source_field == "al_updated_contact_no":
        return "DANLAW"
    if (remark or "").strip().upper() == "IALERT ISSUE":
        return "AL"
    return "FOLLOW-UP"


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

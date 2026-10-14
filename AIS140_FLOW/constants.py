TERMINAL_STATUSES = frozenset([
    "Permanent",
    "Temp + Perm",
    "Cancelled",
    "Reject",
    "Third Party Device-Rejected",
])

COMPLETION_DATE_TRIGGER_STATUSES = frozenset([
    "Temporary", "Permanent", "Cancelled", "Third Party Device-Rejected",
])

TEMP_CERT_DEFAULT_YES_STATES = frozenset([
    "KARNATAKA", "TAMIL NADU", "HIMACHAL PRADESH", "WEST BENGAL",
])
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
    # Keys are upper-case: get_responsibility() upper-cases the remark
    # before looking it up. These two are the certificate-upload events.
    "TEMPORARY CERTIFICATE UPLOADED": "RTO",
    "PERMANENT CERTIFICATE UPLOADED": "CLOSED",
}

RESPONSIBILITY_CHOICES = [
    ("AL", "AL"),
    ("CUSTOMER", "CUSTOMER"),
    ("DANLAW", "DANLAW"),
    ("DEALER/CUSTOMER", "DEALER/CUSTOMER"),
    ("CLOSED", "CLOSED"),
]


def get_responsibility(source_field, remark):
    if source_field == "al_remarks":
        return "AL"
    if source_field == "reupdated_request_al":
        return "DANLAW"
    if not remark:
        return ""
    return RESPONSIBILITY_MAP.get(str(remark).strip().upper(), "")

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

ENGINEER_EMAIL_MAP = {}
STATE_EXTRA_EMAILS = {}
PART_A_ASSIGNMENT_CC = []

# ---------------------------------------------------------------------------
# Show-stopper (request remark pushed) and completion (certificate uploaded)
# e-mails. Recipients = assigned engineer, customer, dealer, additional mail
# id, TSM, plus these fixed addresses.
# ---------------------------------------------------------------------------
AIS140_FIXED_RECIPIENTS = [
    "Venkatasubramanian.S@shokleyland.com",
    "Kry_karthikeyan@shokleyland.com",
]
SHOW_STOPPER_CC = [
    "sales@anlawtech.com",
    "dilipkumarn@anlawtech.com",
]
COMPLETION_CC = [
    "sales@anlawtech.com",
    "naredrareddyg@anlawtech.com",
    "dilipkumarn@anlawtech.com",
]
COMPLETION_STATE_EXTRA_EMAILS = {
    "KARNATAKA": ["sales.hubli@amlmotors.com"],
}

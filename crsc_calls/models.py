# =============================================================================
# crsc_calls — models.py
# Grounded in the original DirectCall model (direct_calls app), simplified
# per the new requirements:
#   - one unified follow-up field set (follow_up_*) instead of separate
#     D1/D2/D3 remark/comment/closure/exp_date/engineer fields
#   - remarks are a fixed, selectable list (not free text)
#   - next_follow_up_exp_date auto-sequenced for iAlert calls
# =============================================================================
from django.core.validators import RegexValidator
from django.db import models
from django.utils.timezone import now

VIN_VALIDATOR = RegexValidator(
    regex=r"^[A-HJ-NPR-Z0-9]{17}$",
    message="VIN must be exactly 17 characters (uppercase letters A-H, J-N, P-R, Z and digits only).",
)
CONTACT_NUMBER_VALIDATOR = RegexValidator(
    regex=r"^\d{10}$", message="Contact Number must be exactly 10 digits.",
)
PSN_VALIDATOR = RegexValidator(
    regex=r"^\d{10}$", message="PSN must be exactly 10 digits.",
)

CALL_TYPE_CHOICES = [
    ("", "Please Select"),
    ("ialert_call", "iAlert Call"),
    ("direct_call", "Direct Call"),
    ("others", "Others"),
]

YES_NO_CHOICES = [("", "Please Select"), ("Yes", "Yes"), ("No", "No")]

COMPLAINT_RAISED_CHOICES = [
    ("", "Please Select"), ("Customer", "Customer"), ("Dealer", "Dealer"),
    ("AL", "AL"), ("iAlert", "iAlert"), ("others", "Others"),
]
COMPLAINT_RAISED_THROUGH_CHOICES = [
    ("", "Please Select"), ("Call", "Call"), ("E-mail", "E-mail"),
    ("iAlert Portal", "iAlert Portal"), ("others", "Others"),
]

# call_status — engineer-visible values plus the manager/admin-only FIR
# closure values (FIR-Repair / FIR-Replace / FIR-Replace_Repair, see
# forms.py::EngineerForm for the role-based split).
CALL_STATUS_CHOICES = [
    ("Pending", "Pending"),
    ("Closed", "Closed"),
    ("Closed-CI", "Closed-CI"),
    ("Resolved", "Resolved"),
    ("Auto-Resolved", "Auto-Resolved"),
    ("D1-D2-D3 Completed", "D1-D2-D3 Completed"),
    ("FIR - For approval", "FIR - For approval"),
    ("FIR-Repair", "FIR-Repair"),
    ("FIR-Replace", "FIR-Replace"),
    ("FIR-Replace_Repair", "FIR-Replace_Repair"),
]
FIR_CLOSURE_STATUSES = {"FIR-Repair", "FIR-Replace", "FIR-Replace_Repair"}

FOLLOW_UP_LEVEL_CHOICES = [("D1", "D1"), ("D2", "D2"), ("D3", "D3")]

PAYMENT_STATUS_CHOICES = [("--", "--"), ("Paid", "Paid"), ("Not paid", "Not paid")]
ENGINEER_RECOMMENDATION_CHOICES = [
    ("--", "--"), ("Repair", "Repair"), ("Replace", "Replace"), ("Replace_Repair", "Replace_Repair"),
]
CHARGEABLE_CHOICES = [("--", "--"), ("Yes", "Yes"), ("No", "No")]


def _char(max_length=100, **kwargs):
    kwargs.setdefault("null", True)
    kwargs.setdefault("blank", True)
    return models.CharField(max_length=max_length, **kwargs)


def _dt(**kwargs):
    kwargs.setdefault("null", True)
    kwargs.setdefault("blank", True)
    return models.DateTimeField(**kwargs)


class DirectCall(models.Model):
    """One CRSC (customer complaint) call, Part-A intake through closure."""

    # ------------------------------------------------------------------
    # Part-A — manager intake
    # ------------------------------------------------------------------
    unique_id = models.CharField(max_length=20, unique=True, blank=True, null=True, editable=False)
    date_of_complaint = models.DateTimeField(default=now)
    complaint_raised_from_location = _char(100, verbose_name="Complaint Raised Location")
    customer_raised_issue = _char(700, verbose_name="Customer Voice")
    complaint_raised = _char(50, choices=COMPLAINT_RAISED_CHOICES, verbose_name="Complaint Raised")
    complaint_raised_by = _char(50, verbose_name="Complaint Raised By")
    contact_number = _char(10, validators=[CONTACT_NUMBER_VALIDATOR], verbose_name="Contact Number")
    customer_mail_id = _char(
        500, verbose_name="Customer Mail ID",
        help_text="Multiple e-mails separated by semicolon (e.g. a@x.com;b@x.com)",
    )
    vehicle_avl_in_workshop = _char(3, choices=YES_NO_CHOICES, verbose_name="Vehicle Available in Workshop")
    complaint_raised_through = _char(50, choices=COMPLAINT_RAISED_THROUGH_CHOICES, verbose_name="Complaint Raised Through")
    complaint_received_by = _char(50)
    vin = _char(17, validators=[VIN_VALIDATOR], verbose_name="VIN")
    psn = _char(10, validators=[PSN_VALIDATOR], verbose_name="Faulty Device PSN Number")
    complaint_assigned_to = _char(100, verbose_name="Engineer Responsible")
    submitted_to_email = models.EmailField(null=True, blank=True, verbose_name="Submitted To Email")
    ialert_remarks = models.TextField(max_length=1000, null=True, blank=True, verbose_name="iAlert Remarks")
    engineer_contact_number = _char(10)
    upload_file = models.FileField(upload_to="crsc_uploads/", null=True, blank=True, verbose_name="Upload File")
    call_type = _char(50, choices=CALL_TYPE_CHOICES, verbose_name="Call Type")
    ialert_ticket_no = _char(50, verbose_name="iAlert Ticket No")
    updated_contact_no = models.TextField(max_length=1400, null=True, blank=True, verbose_name="Alternate Contact Number")
    ialert_tk_timestamp = _dt(verbose_name="iAlert Ticket Timestamp")
    mail_rec_timestamp = _dt(verbose_name="Mail Received Timestamp")

    # ------------------------------------------------------------------
    # Part-B — engineer / Darby-sourced vehicle & device data
    # ------------------------------------------------------------------
    end_customer_mail_id = models.EmailField(null=True, blank=True, verbose_name="End Customer Mail ID")
    veh_reg_no = _char(100, verbose_name="Vehicle Regn No")
    region = _char(50)
    vehicle_type = _char(100)
    vehicle_running_location = _char(100)
    state = _char(100)
    device_model = _char(100)
    telco_status = _char(50)
    active_profile = _char(50)
    activation_start_date = _dt()
    activation_end_date = _dt()
    vehicle_sale_date = models.DateField(null=True, blank=True)
    first_communication_in_darby = _dt()
    last_communication_in_darby = _dt()
    S_trigger_date = _dt(verbose_name="S Trigger Date")
    s_trigger_completion_date = _dt()
    C_trigger_date = _dt(verbose_name="C Trigger Date")
    vehicle_run_kilometers = _char(50)
    kilometers_hours = models.IntegerField(null=True, blank=True)
    main_battery_voltage = models.FloatField(null=True, blank=True, default=0)
    veh_model = _char(100, verbose_name="Vehicle Model")
    engine_type = _char(100)

    call_status = _char(50, choices=CALL_STATUS_CHOICES, default="Pending")
    date_of_closure = _dt()
    contact_person_name = _char(100)
    contact_person_number = _char(10, validators=[CONTACT_NUMBER_VALIDATOR])
    contact_category = _char(50)
    exist_software = _char(100, verbose_name="Existing Software")
    updated_software = _char(100)
    issue_identified = _char(100)
    issue_analysis = _char(200)
    issue_category = models.TextField(null=True, blank=True)
    dealer_name = _char(200)
    al_mfg_plant = _char(100)
    call_closure_category = _char(100)
    nrd_category = _char(100)
    card_status = _char(100)

    Latency_7_days = models.TextField(max_length=100, null=True, blank=True, verbose_name="Latency Last 7 Days")
    V_packet_7_days = models.TextField(max_length=100, null=True, blank=True, verbose_name="V Packet Last 7 Days")
    Latency_3_months = models.TextField(max_length=100, null=True, blank=True, verbose_name="Latency Last 3 Months")
    V_packet_3_months = models.TextField(max_length=100, null=True, blank=True, verbose_name="V Packet Last 3 Months")
    final_analysis = models.TextField(max_length=200, null=True, blank=True, verbose_name="Final Analysis")
    finalised_issue_category = _char(100)
    upload_file_01 = models.FileField(upload_to="crsc_uploads/", null=True, blank=True, verbose_name="Analysis File")

    engineer_recommendation = _char(40, choices=ENGINEER_RECOMMENDATION_CHOICES, default="--")
    hod_comment = models.TextField(null=True, blank=True, verbose_name="HOD Comment")
    chargable_or_not = _char(40, choices=CHARGEABLE_CHOICES, default="--", verbose_name="Chargeable or Not")
    payment_status = _char(10, choices=PAYMENT_STATUS_CHOICES)
    remarks = models.TextField(null=True, blank=True)

    # FIR — For Approval sub-fields (mandatory only when call_status is FIR)
    external_modification = models.TextField(null=True, blank=True)
    device_IMEI = _char(15, verbose_name="Device IMEI")
    device_ICCID = _char(20, verbose_name="Device ICCID")
    device_to_be_sent = _char(50, verbose_name="Faulty Device Sent to Location")
    dealer_address = models.TextField(null=True, blank=True)

    # ------------------------------------------------------------------
    # Unified follow-up (replaces D1 / D2 / D3)
    # ------------------------------------------------------------------
    follow_up_level = _char(2, choices=FOLLOW_UP_LEVEL_CHOICES, verbose_name="Follow-Up Level")
    follow_up_remark = _char(150, verbose_name="Follow-Up Remark")
    follow_up_comment = models.TextField(null=True, blank=True, verbose_name="Follow-Up Comment")
    follow_up_engineer = _char(150, verbose_name="Follow-Up Engineer")
    follow_up_closure_date = _dt(verbose_name="Follow-Up Closure Date")
    next_follow_up_exp_date = _dt(verbose_name="Next Follow-Up Expected Date")
    al_updated_contact_no = models.TextField(null=True, blank=True, verbose_name="AL Updated Contact No")
    follow_up_locked = models.BooleanField(default=False, editable=False)

    # Per-field timestamps, same reasoning as AIS140 REQ-06 — lets the
    # latest-event engine tell which of these changed most recently.
    follow_up_updated_at = _dt()
    al_updated_contact_no_updated_at = _dt()

    d1_tat = _char(20)
    d2_tat = _char(20)
    total_tat = _char(20)

    def save(self, *args, **kwargs):
        if not self.unique_id:
            self.unique_id = self._generate_unique_id()
        super().save(*args, **kwargs)

    def _generate_unique_id(self):
        current = now()
        prefix = f"DTILDC-{current.strftime('%y%m')}"
        last = (
            DirectCall.objects.filter(unique_id__startswith=prefix)
            .order_by("-unique_id").values("unique_id").first()
        )
        next_num = 1073
        if last:
            try:
                next_num = int(last["unique_id"][-4:]) + 1
            except (ValueError, IndexError):
                pass
        while True:
            candidate = f"{prefix}{next_num:04d}"
            if not DirectCall.objects.filter(unique_id=candidate).exists():
                return candidate
            next_num += 1

    def __str__(self):
        return f"CRSC Call {self.unique_id} — VIN {self.vin}"


class DirectCallUpdate(models.Model):
    """Append-only audit trail — same pattern as AIS140RequestUpdate (REQ-09)."""

    SOURCE_CHOICES = [
        ("follow_up", "Follow-Up"),
        ("al_updated_contact_no", "AL Updated Contact No"),
    ]

    call = models.ForeignKey(DirectCall, on_delete=models.CASCADE, related_name="history", null=True, blank=True)
    unique_id = models.CharField(max_length=20, db_index=True)
    vin_no = models.CharField(max_length=17, blank=True, null=True)

    follow_up_level = models.CharField(max_length=2, blank=True, null=True)
    remark = models.TextField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    event_datetime = models.DateTimeField(blank=True, null=True, db_index=True)
    next_follow_up_exp_date = models.DateTimeField(blank=True, null=True)
    al_updated_contact_no = models.TextField(blank=True, null=True)
    responsibility = models.CharField(max_length=50, blank=True, null=True)
    engineer = models.CharField(max_length=150, blank=True, null=True)
    source_field = models.CharField(max_length=30, choices=SOURCE_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-event_datetime", "-created_at"]
        indexes = [models.Index(fields=["unique_id"]), models.Index(fields=["-event_datetime"])]

    def __str__(self):
        return f"{self.unique_id} — {self.source_field} @ {self.event_datetime}"

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
    ("iAlert Call", "iAlert Call"),
    ("Direct Call", "Direct Call"),
    ("Plant Call", "Plant Call"),  
    ("Switch Call", "Switch Call"),  
    ("others", "Others"),
]

YES_NO_CHOICES = [("", "Please Select"), ("Yes", "Yes"), ("No", "No")]

VEHICLE_TYPE_CHOICES = [
    ("", "Please Select"),
    ("--", "--"),
    ("Tipper", "Tipper"),
    ("E-com", "E-com"),
    ("Boss", "Boss"),
    ("Haulage", "Haulage"),
    ("Passenger", "Passenger"),
    ("LCV", "LCV"),
    ("EV-LCV", "EV-LCV"),
    ("EV M&HV", "EV M&HV"),
    ("T&T", "T&T"),
    ("Others", "Others"),
]

ISSUE_IDENTIFIED_CHOICES = [
    ("", "Please Select"),
    ("Not Powering ON", "Not Powering ON"),
    ("No Periodic-Data", "No Periodic-Data"),
    ("100% V Packet", "100% V Packet"),
    ("Partial V Packet", "Partial V Packet"),
    ("Latency", "Latency"),
    ("Data Loss", "Data Loss"),
    ("Future Date", "Future Date"),
    ("CAN Issue", "CAN Issue"),
    ("Sim- Reg Issue", "Sim- Reg Issue"),
    ("SIM- Terminated", "SIM- Terminated"),
    ("Not Latching BSNL - PLANT MODE", "Not Latching BSNL - PLANT MODE"),
    ("Not Latching BSNL - ANY NETWORK", "Not Latching BSNL - ANY NETWORK"),

    ("Veh Wriring Issue", "Veh Wriring Issue"),
    ("Veh Fuse Issue", "Veh Fuse Issue"),
    ("NRD", "NRD"),
    ("Others", "Others"),
]

COMPLAINT_RAISED_CHOICES = [
    ("", "Please Select"), ("Customer", "Customer"), ("Dealer", "Dealer"),
    ("AL", "AL"), ("Plant", "Plant"), ("others", "Others"),
]
COMPLAINT_RAISED_THROUGH_CHOICES = [
    ("", "Please Select"), ("Phone Call", "Phone Call"), ("E-mail", "E-mail"),
    ("iAlert Portal", "iAlert Portal"), ("I-Alert PD API", "I-Alert PD API"), ("others", "Others"),
]

CALL_STATUS_CHOICES = [
    ("Pending", "Pending"),
    ("Closed", "Closed"),
    ("Closed-CI", "Closed-CI"),
    ("Resolved", "Resolved"),
    ("Auto-Resolved", "Auto-Resolved"),
    ("D1-D2-D3 Completed", "D1-D2-D3 Completed"),
    ("Cancelled", "Cancelled"),

    ("FIR - For approval", "FIR - For approval"),
    ("FIR-Repair", "FIR-Repair"),
    ("FIR-Replace", "FIR-Replace"),
    ("FIR-Replace_Repair", "FIR-Replace_Repair"),
]
FIR_CLOSURE_STATUSES = {"FIR-Repair", "FIR-Replace", "FIR-Replace_Repair"}

FOLLOW_UP_LEVEL_CHOICES = [("D1", "D1"), ("D2", "D2"), ("D3", "D3")]
CUSTOMER_CLOSURE_STATUSES = {"Closed", "Closed-CI", "Cancelled","Resolved", "Auto-Resolved", "D1-D2-D3 Completed"}
ENGINEER_RECOMMENDATION_CHOICES = [
    ("--", "--"), ("Repair", "Repair"), ("Replace", "Replace"), ("Replace_Repair", "Replace_Repair"),
]
PAYMENT_STATUS_CHOICES = [("--", "--"), ("Paid", "Paid"), ("Not paid", "Not paid")]
NOT_APPLICABLE = "Not Applicable"
PLANT_STATUS_CHOICES = [(NOT_APPLICABLE, NOT_APPLICABLE), ("Pending", "Pending"), ("Closed", "Closed")]
CHARGEABLE_CHOICES = [("--", "--"), ("Yes", "Yes"), ("No", "No")]

DEVICE_SENT_LOCATION_CHOICES = [
    ("", "Please Select"), ("Goa", "Goa"), ("Hyderabad", "Hyderabad"), ("Chennai", "Chennai"),
]

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
    request_received_timestamp = _dt(verbose_name="Request Received Timestamp")

    complaint_raised_from_location = _char(100, verbose_name="Complaint Raised Location")
    customer_raised_issue = _char(700, verbose_name="Customer Voice")
    complaint_raised = _char(50, choices=COMPLAINT_RAISED_CHOICES, verbose_name="Complaint Raised")
    complaint_raised_by = _char(50, verbose_name="Complaint Raised By")
    contact_number = _char(10, validators=[CONTACT_NUMBER_VALIDATOR], verbose_name="Contact Number")
    customer_mail_id = _char(
        500, verbose_name="Customer Mail ID",
        help_text="Multiple e-mails separated by semicolon (e.g. a@x.com;b@x.com)"
    )
    vehicle_avl_in_workshop = _char(3, choices=YES_NO_CHOICES, verbose_name="Vehicle Available in Workshop")
    complaint_raised_through = _char(50, choices=COMPLAINT_RAISED_THROUGH_CHOICES, verbose_name="Complaint Raised Through")
    complaint_received_by = _char(50,verbose_name="Complaint Received By")
    vin = _char(17, validators=[VIN_VALIDATOR], verbose_name="VIN")
    psn = _char(10, validators=[PSN_VALIDATOR], verbose_name="Faulty Device PSN")
    complaint_assigned_to = _char(100, verbose_name="Engineer Responsible")
    assigned_date = _dt(verbose_name="Assigned Date")
    submitted_to_email = models.EmailField(null=True, blank=True, verbose_name="Engineer Email")
    ialert_remarks = models.TextField(max_length=1000, null=True, blank=True, verbose_name="iAlert Remarks")
    engineer_contact_number = _char(10, validators=[CONTACT_NUMBER_VALIDATOR], verbose_name="Engineer Contact Number")
    call_type = _char(50, choices=CALL_TYPE_CHOICES, verbose_name="Call Type")
    ialert_ticket_no = _char(50, verbose_name="iAlert Ticket No")

    upload_file = models.FileField(upload_to="crsc_uploads/", null=True, blank=True, verbose_name="Upload File")

    end_customer_mail_id = models.EmailField(null=True, blank=True, verbose_name="Additional Customer Mail ID")
    veh_reg_no = _char(100, verbose_name="Vehicle Regn No")
    vehicle_type = _char(100, choices=VEHICLE_TYPE_CHOICES, verbose_name="Vehicle Type")
    vehicle_running_location = _char(100, verbose_name="Vehicle Running Location")
    state = _char(100, verbose_name="State")
    device_model = _char(100, verbose_name="Device Model")
    telco_status = _char(50, verbose_name="Telco Status")
    active_profile = _char(50, verbose_name="Active Profile")
    activation_start_date = _dt(verbose_name="Activation Start Date")
    activation_end_date = _dt(verbose_name="Activation End Date")
    vehicle_sale_date = models.DateField(null=True, blank=True, verbose_name="Vehicle Sale Date")
    first_communication_in_darby = _dt(verbose_name="First Communication in Darby")
    last_communication_in_darby = _dt(verbose_name="Last Communication in Darby")
    S_trigger_date = _dt(verbose_name="S Trigger Req Date")
    s_trigger_completion_date = _dt(verbose_name="S Trigger Completion Date")
    C_trigger_date = _dt(verbose_name="C Trigger Req Date")
    c_trigger_completion_date = _dt(verbose_name="C Trigger Completion Date")
    kilometers_hours = models.IntegerField(null=True, blank=True,verbose_name="Kilometers / Hours")
    main_battery_voltage = models.FloatField(null=True, blank=True, default=0,verbose_name="Main Battery Voltage")
    veh_model = _char(100, verbose_name="Vehicle Model")
    engine_type = _char(100, verbose_name="Engine Type")

    call_status = _char(50, choices=CALL_STATUS_CHOICES, default="Pending", verbose_name="Call Status")
    date_of_closure = _dt(verbose_name="Date of Closure")
    rating = models.IntegerField(null=True, blank=True, verbose_name="Rating")
    customer_feedback = models.TextField(max_length=250, null=True, blank=True, verbose_name="Customer Feedback")
    customer_confirmation = _char(20, verbose_name="Customer Confirmation")
    customer_satisfaction = _char(20, verbose_name="Customer Satisfaction")
    feedback_submission_datetime = _dt(verbose_name="Feedback Submission Datetime")
    feedback_requested_at = _dt(verbose_name="Feedback Requested At")
    exist_software = _char(100, verbose_name="Existing Software")
    updated_software = _char(100, verbose_name="Updated Software")
    issue_identified = _char(100, choices=ISSUE_IDENTIFIED_CHOICES, verbose_name="Issue Identified")
    issue_analysis = _char(200, verbose_name="Final Analysis")
    issue_analysis = models.TextField(max_length=200, null=True, blank=True, verbose_name="Final Analysis")
    dealer_name = _char(200, verbose_name="Dealer Name")
    al_mfg_plant = _char(100, verbose_name="Manufacturer Plant")
    nrd_category = _char(100, verbose_name="NRD Category")
    card_status = _char(100, verbose_name="Card Status")

    Latency_7_days = models.TextField(max_length=100, null=True, blank=True, verbose_name="Latency Last 7 Days")
    V_packet_7_days = models.TextField(max_length=100, null=True, blank=True, verbose_name="V Packet Last 7 Days")
    Latency_3_months = models.TextField(max_length=100, null=True, blank=True, verbose_name="Latency Last 3 Months")
    V_packet_3_months = models.TextField(max_length=100, null=True, blank=True, verbose_name="V Packet Last 3 Months")
    upload_file_01 = models.FileField(upload_to="crsc_uploads/", null=True, blank=True, verbose_name="Analysis File")

    engineer_recommendation = _char(40, choices=ENGINEER_RECOMMENDATION_CHOICES, default="--", verbose_name="Engineer Recommendation")
    chargable_or_not = _char(40, choices=CHARGEABLE_CHOICES, default="--", verbose_name="Chargeable or Not")
    remarks = models.TextField(null=True, blank=True, verbose_name="Remarks")
    payment_status = _char(10, choices=PAYMENT_STATUS_CHOICES)
    hod_comment = models.TextField(null=True, blank=True, verbose_name="HOD Comment")

    # FIR — For Approval sub-fields (mandatory only when call_status is FIR)
    external_modification = models.TextField(null=True, blank=True)
    device_IMEI = _char(15, verbose_name="Device IMEI")
    device_ICCID = _char(20, verbose_name="Device ICCID")
    device_to_be_sent = _char(
        50, choices=DEVICE_SENT_LOCATION_CHOICES, verbose_name="Faulty Device Sent to Location"
    )
    dealer_address = models.TextField(null=True, blank=True, verbose_name="Dealer Address")


    faulty_device_shipped_date = models.DateField(null=True, blank=True, verbose_name="Faulty Device Shipped Date")
    faulty_device_shipped_thru = _char(100, verbose_name="Faulty Device Shipped Thru")
    faulty_device_shipped_lr_details = _char(200, verbose_name="Faulty Device Shipped LR Details")
    faulty_device_reached_date = models.DateField(null=True, blank=True, verbose_name="Faulty Device Reached Date")
    faulty_device_confirmation = _char(200, verbose_name="Faulty Device Confirmation from Plant")
    new_device_serial_no = _char(50, verbose_name="Repaired/New Device Serial No")
    validity_transfer_completed = _char(3, choices=YES_NO_CHOICES, verbose_name="Validity Transfer Completed")
    mapping_completed = _char(3, choices=YES_NO_CHOICES, verbose_name="Mapping Completed")
    commercial_expiry_date = models.DateField(null=True, blank=True, verbose_name="Commercial Expiry Date")
    new_device_fitted_in_vehicle = _char(3, choices=YES_NO_CHOICES, verbose_name="Repaired/New Device Fitted in Vehicle")
    new_device_working = _char(3, choices=YES_NO_CHOICES, verbose_name="Repaired/New Device Working")

    rr_responsibility = _char(100, verbose_name="RR Responsibility")

    # ------------------------------------------------------------------
    # Plant update — filled in by the plant login (Hyderabad / Goa) that the
    # faulty device was sent to. See the /crsc/plant/ screens.
    # ------------------------------------------------------------------
    plant_status = _char(20, choices=PLANT_STATUS_CHOICES, default=NOT_APPLICABLE, verbose_name="Plant Status")
    copq_labour = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="CoPQ Labour")
    copq_material = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="CoPQ Material")
    materials_used = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Materials Used")
    plant_analysis = models.TextField(null=True, blank=True, verbose_name="Plant Analysis")
    plant_conclusion = models.TextField(null=True, blank=True, verbose_name="Plant Conclusion")
    device_shipped_date = models.DateField(null=True, blank=True, verbose_name="Device Shipped Date")
    device_shipped_through = _char(100, verbose_name="Device Shipped Through")
    device_shipped_lr_no = _char(100, verbose_name="Device Shipped LR No")

    follow_up_level = _char(2, choices=FOLLOW_UP_LEVEL_CHOICES, verbose_name="Follow-Up Level")
    follow_up_remark = _char(150, verbose_name="Follow-Up Remark")
    follow_up_comment = models.TextField(null=True, blank=True, verbose_name="Follow-Up Comment")
    follow_up_engineer = _char(150, verbose_name="Follow-Up Engineer")
    next_follow_up_exp_date = _dt(verbose_name="Next Follow-Up Expected Date")
    al_updated_contact_no = models.TextField(null=True, blank=True, verbose_name="Alternate/Updated Contact No")

    follow_up_updated_at = _dt(verbose_name="Follow-Up Updated At")
    al_updated_contact_no_updated_at = _dt(verbose_name="Alternate/Updated Contact No Updated At")

    responsibility = _char(50, verbose_name="Responsibility")

    d1_tat = _char(20, verbose_name="D1 TAT")
    d2_tat = _char(20, verbose_name="D2 TAT")
    total_tat = _char(20, verbose_name="Total TAT")

    def compute_rr_responsibility(self):
        """Who has to act next on a FIR repair/replace call. The first
        unfinished step wins:
          1. Faulty Device Shipped LR Details not updated -> the engineer
          2. Faulty Device Confirmation from Plant not updated -> Manager
          3. Plant Status still Pending -> the plant (its location name)
          4. Repaired/New Device Working not updated -> Manager
        "Closed" once everything is done; "Not Applicable" when the call isn't
        in a FIR closure status."""
        if (self.call_status or "") not in FIR_CLOSURE_STATUSES:
            return NOT_APPLICABLE

        def blank(value):
            return value is None or str(value).strip() == ""

        if blank(self.faulty_device_shipped_lr_details):
            return (self.complaint_assigned_to or "").strip() if (self.complaint_assigned_to or "--") != "--" else "Engineer"
        if blank(self.faulty_device_confirmation):
            return "Manager"
        if (self.plant_status or "Pending") != "Closed":
            return self.device_to_be_sent or "Plant"
        if blank(self.new_device_working):
            return "Manager"
        return "Closed"

    def save(self, *args, **kwargs):
        if not self.unique_id:
            self.unique_id = self._generate_unique_id()
        # Plant Status only means something once the call is a FIR repair /
        # replace case: Pending from then on, "Not Applicable" before that.
        in_fir = (self.call_status or "") in FIR_CLOSURE_STATUSES
        if in_fir and self.plant_status in (None, "", NOT_APPLICABLE):
            self.plant_status = "Pending"
        elif not in_fir and self.plant_status in (None, "", "Pending"):
            self.plant_status = NOT_APPLICABLE
        self.rr_responsibility = self.compute_rr_responsibility()
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            extra = [f for f in ("plant_status", "rr_responsibility") if f not in update_fields]
            if extra:
                kwargs["update_fields"] = list(update_fields) + extra
        super().save(*args, **kwargs)

    def _generate_unique_id(self):
        current = now()
        prefix = f"DTILDC-{current.strftime('%y%m')}"
        last = (
            DirectCall.objects.filter(unique_id__startswith=prefix)
            .order_by("-unique_id").values("unique_id").first()
        )
        next_num = 1
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
    next_follow_up_exp_date = models.DateField(blank=True, null=True)
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

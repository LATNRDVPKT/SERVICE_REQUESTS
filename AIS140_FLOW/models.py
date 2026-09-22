# =============================================================================
# AIS140_FLOW — models.py
# =============================================================================
# AIS140Request        — the single ticket table covering the full lifecycle
# AIS140RequestUpdate   — append-only audit/history table (REQ-09)
# =============================================================================

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils.timezone import now

iccid_validator = RegexValidator(r"^\d{20}$", "ICCID No must be exactly 20 digits.")
imei_validator = RegexValidator(r"^\d{15}$", "IMEI No must be exactly 15 digits.")
vin_validator = RegexValidator(r"^[A-Za-z0-9]{17}$", "Chassis No (VIN) must be exactly 17 alphanumeric characters.")
psn_validator = RegexValidator(r"^\d{10}$", "PSN No must be exactly 10 digits.")
phone_validator = RegexValidator(r"^\d{10}$", "Phone number must be exactly 10 digits.")


# ---------------------------------------------------------------------------
# Choice constants
# ---------------------------------------------------------------------------
TEMP_CERT_CHOICES = [("Yes", "Yes"), ("No", "No")]

UPDATE_TO_AL_API_CHOICES = [
    ("", "Not determined yet"),
    ("Permanent", "Permanent"),
    ("Temporary", "Temporary"),
    ("Temp + Perm", "Temp + Perm"),
    ("Request", "Request"),
]

COMPLETION_STATUS_CHOICES = [
    ("Pending", "Pending"),
    ("Temporary", "Temporary"),
    ("Permanent", "Permanent"),
    ("Temp + Perm", "Temp + Perm"),
    ("Cancelled", "Cancelled"),
    ("Reject", "Reject"),
    ("Third Party Device-Rejected", "Third Party Device-Rejected"),
]


def _char(max_length=100, **kwargs):
    kwargs.setdefault("null", True)
    kwargs.setdefault("blank", True)
    return models.CharField(max_length=max_length, **kwargs)


def _email(**kwargs):
    kwargs.setdefault("null", True)
    kwargs.setdefault("blank", True)
    return models.EmailField(**kwargs)


def _dt(**kwargs):
    kwargs.setdefault("null", True)
    kwargs.setdefault("blank", True)
    return models.DateTimeField(**kwargs)


def _file(**kwargs):
    kwargs.setdefault("null", True)
    kwargs.setdefault("blank", True)
    kwargs.setdefault("upload_to", "certificates/")
    return models.FileField(**kwargs)


class AIS140Request(models.Model):
    """Full lifecycle record for one AIS140 certification request."""

    # ------------------------------------------------------------------
    # Ticket metadata
    # ------------------------------------------------------------------
    unique_id = models.CharField(
        max_length=20, unique=True, blank=True, null=True, editable=False,
        verbose_name="Unique ID",
        help_text="Auto-generated on first save. Format: DTILAIS-YYMM####",
    )
    request_id = _char(50, verbose_name="AL Request ID")
    ticket_through = _char(50, verbose_name="Ticket Through")

    # ------------------------------------------------------------------
    # Dates
    # ------------------------------------------------------------------
    date_of_request = models.DateTimeField(verbose_name="AL Assigned Date")
    Customer_assigned_date = models.DateTimeField(verbose_name="Assigned to Engineer Date")
    AL_assigned_date = _dt(verbose_name="A.L Assigned Date")
    reupdated_request_al = _dt(verbose_name="Updated To DTIL")
    reupdated_request_al_updated_at = _dt(verbose_name="Updated To DTIL — Last Changed")

    # ------------------------------------------------------------------
    # Customer details
    # ------------------------------------------------------------------
    customer_name = _char(100, verbose_name="Customer Name")
    # max_length kept at 15 (not 10) — existing production rows have an
    # 11-digit value (leading 0 trunk prefix); the validator still enforces
    # exactly 10 digits for every new save going forward.
    customer_phone = _char(15, verbose_name="Customer Phone", validators=[phone_validator])
    Customer_mobile_number = _char(10, validators=[phone_validator])
    Customer_Alternate_number = _char(10, verbose_name="Cust Alt Contact No", validators=[phone_validator])
    Customer_Email_ID = _email()
    Cust_veh_Regn_Address = models.TextField(null=True, blank=True, verbose_name="Cust Veh Regn Address")
    Cust_veh_Regn_Pincode = _char(50)
    pan_card = _char(50, verbose_name="PAN No")
    aadhar_card = _char(50, verbose_name="AADHAR No")
    vahan_date = _dt(verbose_name="Vahan Date")
    vahan_uploaded_by = _char(50, verbose_name="Vahan Uploaded By")

    # ------------------------------------------------------------------
    # Vehicle details
    # ------------------------------------------------------------------
    # max_length kept at 50 (not the strict 17) because at least one existing
    # production row is 18 chars — shrinking the column would break a MySQL
    # ALTER TABLE on deploy. The validator still enforces exactly 17
    # alphanumeric characters for every new save going forward.
    vin_no = _char(50, verbose_name="Chassis No", validators=[vin_validator])
    engine = _char(50, verbose_name="Engine No")
    vehicle_no = _char(50, verbose_name="Vehicle Regn No")
    vehicle_model = _char(100, verbose_name="Vehicle Model")
    manufacturing_year = _char(50, verbose_name="Manufacturing Year")
    AIS140_Type = _char(50, verbose_name="AIS140 Type")

    # ------------------------------------------------------------------
    # Dealer / RTO / Location
    # ------------------------------------------------------------------
    dealer_name = _char(100, verbose_name="Dealer Name")
    dealer_code = _char(50, verbose_name="Dealer Code")
    Dealer_mail = _char(250)
    Dealer_Contact = _char(10, validators=[phone_validator])
    Dealer_Location = _char(100)
    Dealer_Email_ID = _email()
    Ialert_Email_ID = _email()
    TSM_mail = _char(50, verbose_name="TSM Mail ID")
    rto_code = _char(50, verbose_name="RTO Code")
    rto_name = _char(100, verbose_name="RTO Name")
    ao_name = _char(100, verbose_name="AO Name")
    ro = _char(100, verbose_name="RO Name")
    zone = _char(100)
    state = _char(100)

    # ------------------------------------------------------------------
    # Request / requestor info
    # ------------------------------------------------------------------
    requested_by = _char(100, verbose_name="Requested By")
    requested_name = _char(100, verbose_name="Requestor Email ID")
    requested_phone_number = _char(10, verbose_name="Requestor Phone Number", validators=[phone_validator])
    request_type = _char(50, default="Please Select")
    category = _char(50, default="--", verbose_name="Category")
    remarks = models.TextField(null=True, blank=True)
    AL_remarks = _char(150)
    AL_comments = _char(150)
    al_remarks_updated_at = _dt(verbose_name="AL Remarks — Last Changed")

    # ------------------------------------------------------------------
    # Assignment
    # ------------------------------------------------------------------
    assigned_to = _char(100)
    assigned_engineer_email = _char(100)
    user_id = _char(50, verbose_name="User ID")
    owner_name = _char(100)
    owner_phone = _char(10, validators=[phone_validator])

    # ------------------------------------------------------------------
    # Device / SIM
    # ------------------------------------------------------------------
    device_model = _char(50, verbose_name="Device Model")
    psn = _char(10, verbose_name="PSN No", validators=[psn_validator])
    icicid_no = _char(20, verbose_name="ICCID No", validators=[iccid_validator])
    imei_no = _char(15, verbose_name="IMEI No", validators=[imei_validator])
    rto_approval_date = models.DateField(null=True, blank=True)
    veh_run_kms = _char(100)
    total_run_kms = _char(100)

    # REQ-13 — Darby device-data fields
    device_product_code = _char(100, verbose_name="Device Product Code")
    device_architecture_type = _char(100, verbose_name="Device Architecture Type")
    device_battery_voltage = _char(50, verbose_name="Device Battery Voltage")
    darby_lookup_status = _char(
        20, default="", verbose_name="Darby Lookup Status",
        help_text="pending / success / not_found / failed",
    )
    darby_lookup_at = _dt(verbose_name="Darby Lookup Time")

    certification_start_date = models.DateField(null=True, blank=True, verbose_name="Certification Start Date")
    certification_end_date = models.DateField(null=True, blank=True, verbose_name="Certification End Date")

    # ------------------------------------------------------------------
    # Certificates
    # ------------------------------------------------------------------
    temp_cert_reqd = _char(10, choices=TEMP_CERT_CHOICES, default="No", verbose_name="Temporary Certificate Required")
    temp_cert_date = _dt()
    temp_raised_by = _char(100, verbose_name="Temporary Raised By")
    permanent_certificate = models.TextField(null=True, blank=True)
    permanent_cert_date = _dt()
    perm_raised_by = _char(100, verbose_name="Permanent Raised By")

    upload_certificate_in_ialert = _file(verbose_name="Upload Certificate in iAlert (Temporary)")
    upload_certificate_in_ialert_01 = _file(verbose_name="Upload Certificate (Permanent)")
    upload_certificate_in_ialert_02 = _file(verbose_name="Upload Certificate (Vahan)")
    upload_certificate_in_danlaw_server = models.TextField(null=True, blank=True)

    temp_cert_updated_at = _dt(verbose_name="Temporary Certificate — Last Changed")
    permanent_cert_updated_at = _dt(verbose_name="Permanent Certificate — Last Changed")

    # ------------------------------------------------------------------
    # Engineer Part-B fields — single show-stopper remark (replaces D1/D2)
    # ------------------------------------------------------------------
    request_remarks = models.TextField(blank=True, null=True, verbose_name="Request Remarks")
    request_comments = models.TextField(blank=True, null=True, verbose_name="Request Comments")
    attending_engineer = _char(255, verbose_name="Attending Engineer")
    request_closure = _dt(verbose_name="Request Closure")
    request_locked = models.BooleanField(default=False, editable=False)
    request_remarks_updated_at = _dt(verbose_name="Request Remarks — Last Changed")

    # ------------------------------------------------------------------
    # iAlert / completion
    # ------------------------------------------------------------------
    Update_to_AL_API = _char(250, choices=UPDATE_TO_AL_API_CHOICES, default="", verbose_name="Update to AL API")
    completion_status = _char(50, choices=COMPLETION_STATUS_CHOICES, default="Pending")
    completion_date = _dt()
    total_tat = _char(100)
    D1_TAT = _char(100)

    responsibility = models.TextField(null=True, blank=True)
    remarks_02 = models.TextField(null=True, blank=True, verbose_name="Remarks")

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------
    communication_status = _char(100)
    mail_to_customer = _char(250)
    additional_email_id = _email()
    engr_to_monitor = _email()

    class Meta:
        indexes = [
            models.Index(fields=["unique_id"]),
            models.Index(fields=["vin_no"]),
            models.Index(fields=["request_id"]),
            models.Index(fields=["completion_status"]),
            models.Index(fields=["assigned_engineer_email"]),
            models.Index(fields=["state"]),
            models.Index(fields=["-date_of_request", "completion_status"]),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            orig = AIS140Request.objects.filter(pk=self.pk).values("request_id").first()
            if orig:
                self.request_id = orig["request_id"]

        if not self.unique_id:
            self.unique_id = self._generate_unique_id()

        super().save(*args, **kwargs)

    def _generate_unique_id(self):
        current = now()
        prefix = f"DTILAIS-{current.strftime('%y%m')}"
        last = (
            AIS140Request.objects
            .filter(unique_id__startswith=prefix)
            .order_by("-unique_id")
            .values("unique_id")
            .first()
        )
        next_num = 1025
        if last:
            try:
                next_num = int(last["unique_id"][-4:]) + 1
            except (ValueError, IndexError):
                pass
        while True:
            candidate = f"{prefix}{next_num:04d}"
            if not AIS140Request.objects.filter(unique_id=candidate).exists():
                return candidate
            next_num += 1

    def clean(self):
        if self.date_of_request is None:
            raise ValidationError("Date of Request cannot be null.")

    def __str__(self):
        date_str = self.date_of_request.isoformat() if self.date_of_request else "No Date"
        return f"AIS140Request {self.unique_id or self.id} — {date_str}"


# =============================================================================
# REQ-09 — Update history / audit trail
# =============================================================================
class AIS140RequestUpdate(models.Model):
    """
    Append-only audit trail. A new row is written every time one of the
    tracked fields on AIS140Request changes (request_remarks, AL_remarks,
    reupdated_request_al, upload_certificate_in_ialert,
    upload_certificate_in_ialert_01). See services/workflow.py.
    """

    SOURCE_CHOICES = [
        ("request_remarks", "Request Remarks"),
        ("al_remarks", "AL Remarks"),
        ("reupdated_request_al", "Reupdated Request AL"),
        ("temporary_certificate", "Temporary Certificate"),
        ("permanent_certificate", "Permanent Certificate"),
    ]

    ticket = models.ForeignKey(
        AIS140Request, on_delete=models.CASCADE, related_name="history",
        null=True, blank=True,
    )
    unique_id = models.CharField(max_length=20, db_index=True)
    vin_no = models.CharField(max_length=50, blank=True, null=True)

    latest_remark = models.TextField(blank=True, null=True)
    latest_comments = models.TextField(blank=True, null=True)
    remark_datetime = models.DateTimeField(blank=True, null=True, db_index=True)

    responsibility = models.CharField(max_length=100, blank=True, null=True)
    attending_engineer = models.CharField(max_length=255, blank=True, null=True)
    source_field = models.CharField(max_length=50, choices=SOURCE_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-remark_datetime", "-created_at"]
        indexes = [
            models.Index(fields=["unique_id"]),
            models.Index(fields=["-remark_datetime"]),
        ]

    def __str__(self):
        return f"{self.unique_id} — {self.source_field} @ {self.remark_datetime}"

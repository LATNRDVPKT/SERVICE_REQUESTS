# =============================================================================
# AIS140_FLOW — forms.py
# =============================================================================
import json

from django import forms
from .models import AIS140Request
from .constants import REQUEST_REMARK_CHOICES, REMARK_COMMENT_MAP

# Part-A mandatory fields (REQ-01)
PART_A_MANDATORY_FIELDS = [
    "assigned_engineer_email",
    "request_type",
    "vin_no",
    "psn",
    "customer_name",
    "customer_phone",
]

PART_A_MANDATORY_LABELS = {
    "assigned_engineer_email": "Assigned Engineer Email",
    "request_type": "Request Type",
    "vin_no": "VIN No",
    "psn": "PSN No",
    "customer_name": "Customer Name",
    "customer_phone": "Customer Phone",
}

# Fields locked once a request remark has been submitted (REQ-03)
REQUEST_LOCKED_FIELDS = ["request_remarks", "request_comments", "attending_engineer"]

DATE_TIME_FIELDS = {
    "date_of_request", "Customer_assigned_date", "AL_assigned_date", "reupdated_request_al",
    "temp_cert_date", "permanent_cert_date", "completion_date",
    "vahan_date",
}
DATE_FIELDS = {"certification_start_date", "certification_end_date", "rto_approval_date"}


def _apply_uniform_widget_style(form):
    """
    Every field gets the same 'form-control' CSS class and, for date/date-
    time model fields, the matching HTML5 input type — so every field in
    the form renders with identical sizing/spacing regardless of whether it
    has a custom widget defined below. This is what keeps Part-A/Part-B
    visually consistent field-to-field.
    """
    for name, field in form.fields.items():
        widget = field.widget
        existing = widget.attrs.get("class", "")
        if "form-control" not in existing:
            widget.attrs["class"] = (existing + " form-control").strip()
        if name in DATE_TIME_FIELDS and isinstance(widget, (forms.DateTimeInput, forms.TextInput)):
            widget.input_type = "datetime-local"
            widget.format = "%Y-%m-%dT%H:%M"
        elif name in DATE_FIELDS and isinstance(widget, (forms.DateInput, forms.TextInput)):
            widget.input_type = "date"
            widget.format = "%Y-%m-%d"
        if isinstance(widget, forms.ClearableFileInput):
            widget.attrs["class"] = "form-control-file"


# =============================================================================
# ManagerForm — Part-A
# =============================================================================
class ManagerForm(forms.ModelForm):
    """Manager form to create or edit a certification request (Part-A)."""

    class Meta:
        model = AIS140Request
        fields = [
            "request_id", "ticket_through",
            "date_of_request", "Customer_assigned_date", "AL_assigned_date",
            "reupdated_request_al",
            "customer_name", "customer_phone", "Customer_Alternate_number",
            "Customer_Email_ID", "Cust_veh_Regn_Address",
            "vin_no", "engine", "vehicle_no", "vehicle_model",
            "manufacturing_year", "AIS140_Type",
            "pan_card", "aadhar_card",
            "device_model", "request_type", "category", "psn",
            "dealer_name", "dealer_code", "Dealer_mail", "rto_code", "rto_name",
            "state", "ao_name", "ro", "zone",
            "requested_by", "requested_name", "requested_phone_number",
            "assigned_to", "assigned_engineer_email",
            "AL_remarks", "AL_comments",
        ]
        widgets = {
            "Cust_veh_Regn_Address": forms.TextInput(attrs={"placeholder": "Enter Customer Address"}),
            "dealer_code": forms.TextInput(attrs={"placeholder": "Enter Dealer Code"}),
            "AL_remarks": forms.TextInput(attrs={"placeholder": "Enter AL Remarks"}),
            "AL_comments": forms.TextInput(attrs={"placeholder": "Enter AL Comments"}),
            "requested_phone_number": forms.TextInput(attrs={"placeholder": "Enter Phone Number"}),
            "assigned_engineer_email": forms.TextInput(attrs={"placeholder": "Enter Assigned Engineer Email"}),
            "request_type": forms.TextInput(attrs={"placeholder": "Enter Request Type"}),
            "vin_no": forms.TextInput(attrs={"placeholder": "Enter VIN / Chassis No"}),
            "psn": forms.TextInput(attrs={"placeholder": "Enter PSN No"}),
            "customer_name": forms.TextInput(attrs={"placeholder": "Enter Customer Name"}),
            "customer_phone": forms.TextInput(attrs={"placeholder": "Enter Customer Phone"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in PART_A_MANDATORY_FIELDS:
            if name in self.fields:
                self.fields[name].required = True
        _apply_uniform_widget_style(self)


# =============================================================================
# PartBForm — Part-B (engineer form)
# =============================================================================
class PartBForm(forms.ModelForm):
    """
    Engineer form to update ticket progress, log a request remark, upload
    certificates, and close tickets.

    Validation behaviour:
      - REQ-12: Update_to_AL_API and completion_status are always required.
      - REQ-03: once request_remarks is already saved (non-blank) on the
        ticket, incoming changes to request_remarks / request_comments /
        attending_engineer are rejected here as a backend safety net (the
        view also enforces this before the form is even bound).
      - For API tickets (request_id present), the matching certificate
        file or the request remark/comments is required depending on
        Update_to_AL_API.
    """

    class Meta:
        model = AIS140Request
        fields = [
            "device_model", "icicid_no", "imei_no", "additional_email_id",
            "attending_engineer", "request_remarks", "request_comments",
            "temp_cert_reqd", "temp_cert_date", "temp_raised_by",
            "upload_certificate_in_ialert",
            "upload_certificate_in_ialert_01",
            "upload_certificate_in_ialert_02",
            "Update_to_AL_API", "completion_status", "completion_date",
            "certification_start_date", "certification_end_date",
            "rto_approval_date", "veh_run_kms", "total_run_kms",
            "vahan_date", "vahan_uploaded_by",
        ]
        widgets = {
            "device_model": forms.TextInput(attrs={"placeholder": "Device Model"}),
            "icicid_no": forms.TextInput(attrs={"placeholder": "Enter ICCID No", "maxlength": "20"}),
            "imei_no": forms.TextInput(attrs={"placeholder": "Enter IMEI No", "maxlength": "17"}),
            "attending_engineer": forms.TextInput(attrs={"placeholder": "Enter Attending Engineer Email"}),
            "request_remarks": forms.Select(
                choices=REQUEST_REMARK_CHOICES,
                attrs={
                    "data-autofill-target": "#id_request_comments",
                    "data-autofill-map": json.dumps(REMARK_COMMENT_MAP),
                },
            ),
            "request_comments": forms.TextInput(attrs={"placeholder": "Enter Request Comments"}),
            "veh_run_kms": forms.TextInput(attrs={"placeholder": "Enter Vehicle Run in Kms"}),
            "total_run_kms": forms.TextInput(attrs={"placeholder": "Enter Vehicle Total Run in Kms"}),
            "vahan_uploaded_by": forms.TextInput(attrs={"placeholder": "Enter Name"}),
            "Update_to_AL_API": forms.Select(attrs={"readonly": "readonly"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # REQ-03 — once request_remarks is already saved, render the trio
        # as disabled in the UI.
        if self.instance and self.instance.pk and (self.instance.request_remarks or "").strip():
            for name in ("request_remarks", "request_comments", "attending_engineer"):
                if name in self.fields:
                    self.fields[name].disabled = True
        # Update_to_AL_API is auto-derived (REQ-04) — never hand-edited.
        if "Update_to_AL_API" in self.fields:
            self.fields["Update_to_AL_API"].disabled = True
        _apply_uniform_widget_style(self)

    def clean(self):
        cleaned = super().clean()
        instance = self.instance

        # REQ-03 — backend lock: reject any change once request_remarks is set
        if instance and instance.pk and (instance.request_remarks or "").strip():
            cleaned["request_remarks"] = instance.request_remarks
            cleaned["request_comments"] = instance.request_comments
            cleaned["attending_engineer"] = instance.attending_engineer

        # REQ-12 — always mandatory
        if not (cleaned.get("completion_status") or "").strip():
            self.add_error("completion_status", "Completion Status is required.")

        # Existing API-ticket validations
        request_id = getattr(instance, "request_id", None)
        if not request_id or not str(request_id).strip():
            return cleaned  # manual ticket — no further API validation

        api_value = (getattr(instance, "_pending_update_to_al_api", None)
                     or cleaned.get("Update_to_AL_API") or "").strip()

        def filled(key):
            v = cleaned.get(key)
            return bool(v and str(v).strip())

        def has_file(field):
            return bool(self.files.get(field) or getattr(self.instance, field, None))

        if api_value == "Request":
            if not filled("request_remarks"):
                self.add_error("request_remarks", "Request Remarks is required when Update to A.L API is Request.")
            if not filled("request_comments"):
                self.add_error("request_comments", "Request Comments is required when Update to A.L API is Request.")
        elif api_value == "Temporary":
            if not has_file("upload_certificate_in_ialert"):
                self.add_error("upload_certificate_in_ialert",
                                "Temporary Certificate is required when Update to A.L API is Temporary.")
        elif api_value == "Permanent":
            if not has_file("upload_certificate_in_ialert_01"):
                self.add_error("upload_certificate_in_ialert_01",
                                "Permanent Certificate is required when Update to A.L API is Permanent.")
        elif api_value == "Temp + Perm":
            if not has_file("upload_certificate_in_ialert"):
                self.add_error("upload_certificate_in_ialert",
                                "Temporary Certificate is required when Update to A.L API is Temp + Perm.")
            if not has_file("upload_certificate_in_ialert_01"):
                self.add_error("upload_certificate_in_ialert_01",
                                "Permanent Certificate is required when Update to A.L API is Temp + Perm.")

        return cleaned

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

DATE_TIME_FIELDS = {
    "date_of_request", "Customer_assigned_date", "AL_assigned_date", "reupdated_request_al",
    "permanent_cert_date",
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
            "vin_no": forms.TextInput(attrs={"placeholder": "Enter VIN / Chassis No", "maxlength": "17"}),
            "psn": forms.TextInput(attrs={"placeholder": "Enter PSN No", "maxlength": "10", "inputmode": "numeric"}),
            "customer_name": forms.TextInput(attrs={"placeholder": "Enter Customer Name"}),
            "customer_phone": forms.TextInput(attrs={"placeholder": "Enter Customer Phone"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in PART_A_MANDATORY_FIELDS:
            if name in self.fields:
                self.fields[name].required = True
        # vin_no's DB column is intentionally wider than 17 (legacy rows up
        # to 18 chars — see models.py), so Django auto-derives maxlength="50"
        # from the model field and clobbers our widget attrs.setdefault above.
        # Force it back to 17 for new data entry; the vin_validator still
        # enforces the exact format server-side regardless.
        if "vin_no" in self.fields:
            self.fields["vin_no"].widget.attrs["maxlength"] = "17"
        _apply_uniform_widget_style(self)


# =============================================================================
# PartBForm — Part-B (engineer form)
# =============================================================================
class PartBForm(forms.ModelForm):
    """
    Engineer form to update ticket progress, log a request remark, upload
    certificates, and close tickets.

    Validation behaviour:
      - REQ-12: completion_status is always required.
      - Request Remarks / Request Comments never lock — engineers can
        update them on every save. The ticket only becomes fully
        read-only once completion_status reaches a terminal state
        (enforced at the view/template level, not here).
      - Attending Engineer is not a form field — the view stamps it from
        the logged-in user on every save (see views.part_b_form), so the
        audit trail always reflects who was actually authenticated.
      - Update_to_AL_API is engineer-selected (Remark / Temporary /
        Permanent) — for AL-API tickets (request_id present and
        ticket_through is "A.L API") it's mandatory, and the matching
        certificate file or request remark/comments is additionally
        required depending on whichever value was chosen.
    """

    class Meta:
        model = AIS140Request
        fields = [
            "device_model", "icicid_no", "imei_no", "additional_email_id",
            "request_remarks", "request_comments",
            "temp_cert_reqd", "temp_raised_by",
            "upload_certificate_in_ialert",
            "upload_certificate_in_ialert_01",
            "upload_certificate_in_ialert_02",
            "Update_to_AL_API", "completion_status",
            "certification_start_date", "certification_end_date",
            "rto_approval_date", "veh_run_kms", "total_run_kms",
            "vahan_date", "vahan_uploaded_by",
        ]
        widgets = {
            "device_model": forms.TextInput(attrs={"placeholder": "Device Model"}),
            "icicid_no": forms.TextInput(attrs={"placeholder": "Enter ICCID No", "maxlength": "20"}),
            "imei_no": forms.TextInput(attrs={"placeholder": "Enter IMEI No", "maxlength": "15"}),
            "request_remarks": forms.Select(
                choices=REQUEST_REMARK_CHOICES,
                attrs={
                    "data-autofill-target": "#id_request_comments",
                    "data-autofill-map": json.dumps(REMARK_COMMENT_MAP),
                },
            ),
            "request_comments": forms.Textarea(attrs={"placeholder": "Enter Request Comments", "rows": 2}),
            "veh_run_kms": forms.TextInput(attrs={"placeholder": "Enter Vehicle Run in Kms"}),
            "total_run_kms": forms.TextInput(attrs={"placeholder": "Enter Vehicle Total Run in Kms"}),
            "vahan_uploaded_by": forms.TextInput(attrs={"placeholder": "Enter Name"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_uniform_widget_style(self)

    def clean(self):
        cleaned = super().clean()
        instance = self.instance

        # REQ-12 — always mandatory
        if not (cleaned.get("completion_status") or "").strip():
            self.add_error("completion_status", "Completion Status is required.")

        def filled(key):
            v = cleaned.get(key)
            return bool(v and str(v).strip())

        def has_file(field):
            return bool(self.files.get(field) or getattr(self.instance, field, None))

        # Whenever Temporary Certificate Required is Yes, the Temporary
        # Certificate file is mandatory — regardless of ticket type.
        if cleaned.get("temp_cert_reqd") == "Yes" and not has_file("upload_certificate_in_ialert"):
            self.add_error(
                "upload_certificate_in_ialert",
                "Upload Certificate in iAlert (Temporary) is required when Temporary Certificate Required is Yes.",
            )

        # Existing API-ticket validations
        request_id = getattr(instance, "request_id", None)
        ticket_through = (getattr(instance, "ticket_through", "") or "").strip().lower()
        is_al_api_ticket = bool(request_id and str(request_id).strip()) and ticket_through in ("a.l api", "al api")
        if not request_id or not str(request_id).strip():
            return cleaned  # manual ticket — no further API validation

        # Update to AL API is engineer-selected (Remark / Temporary /
        # Permanent) — the matching remark or certificate is mandatory for
        # whichever value was actually chosen.
        api_value = (cleaned.get("Update_to_AL_API") or "").strip()

        if is_al_api_ticket and not api_value:
            self.add_error("Update_to_AL_API", "Update to AL API is required.")

        if api_value == "Remark":
            if not filled("request_remarks"):
                self.add_error("request_remarks", "Request Remarks is required when Update to A.L API is Remark.")
            if not filled("request_comments"):
                self.add_error("request_comments", "Request Comments is required when Update to A.L API is Remark.")
        elif api_value == "Temporary":
            if not has_file("upload_certificate_in_ialert"):
                self.add_error("upload_certificate_in_ialert",
                                "Temporary Certificate is required when Update to A.L API is Temporary.")
        elif api_value == "Permanent":
            if not has_file("upload_certificate_in_ialert_01"):
                self.add_error("upload_certificate_in_ialert_01",
                                "Permanent Certificate is required when Update to A.L API is Permanent.")

        return cleaned

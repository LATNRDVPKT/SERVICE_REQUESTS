import json

from django import forms

from .constants import remark_choices_for, REMARK_COMMENT_MAP, ALL_REMARKS
from .models import DirectCall, CALL_STATUS_CHOICES, FIR_CLOSURE_STATUSES
from .services.plant import PLANT_EDIT_KEYS, PLANT_LABELS, PLANT_REQUIRED_WHEN_CLOSED

PART_A_MANDATORY_FIELDS = ["vin", "contact_number", "complaint_assigned_to", "call_type"]
PART_A_MANDATORY_LABELS = {
    "vin": "VIN",
    "contact_number": "Contact Number",
    "complaint_assigned_to": "Engineer Responsible",
    "call_type": "Call Type",
}

# Faulty-device logistics / replacement follow-through. Editable (by engineers
# and admins) only while call_status is a FIR closure status, and each field
# locks for good as soon as it holds a value.
FIR_FLOW_FIELDS = [
    "faulty_device_shipped_date", "faulty_device_shipped_thru", "faulty_device_shipped_lr_details",
    "faulty_device_reached_date", "faulty_device_confirmation", "new_device_serial_no",
    "mapping_completed", "validity_transfer_completed", "commercial_expiry_date",
    "new_device_fitted_in_vehicle", "new_device_working",
]

# Mandatory for every call_status except "Pending".
NON_PENDING_MANDATORY_FIELDS = [
    ("issue_identified", "Issue Identified"),
    ("issue_analysis", "Issue Analysis"),
    ("kilometers_hours", "Kilometers/Hours"),
    ("main_battery_voltage", "Main Battery Voltage"),
    ("device_model", "Device Model"),
    ("exist_software", "Existing Software"),
    ("updated_software", "Updated Software"),
]
# Statuses that additionally require Faulty Device Sent to Location,
# Dealer Address and Engineer Recommendation.
FIR_MANDATORY_STATUSES = {"FIR - For approval"} | set(FIR_CLOSURE_STATUSES)

DATE_TIME_FIELDS = {
    "date_of_complaint", "request_received_timestamp",
    "activation_start_date", "activation_end_date", "first_communication_in_darby",
    "last_communication_in_darby", "S_trigger_date", "s_trigger_completion_date",
    "C_trigger_date", "c_trigger_completion_date", "date_of_closure",
}
DATE_FIELDS = {"next_follow_up_exp_date", "vehicle_sale_date", "faulty_device_shipped_date",
                "faulty_device_reached_date", "commercial_expiry_date"}

def _apply_uniform_widget_style(form):
    for name, field in form.fields.items():
        widget = field.widget
        existing = widget.attrs.get("class", "")
        if "form-control" not in existing:
            widget.attrs["class"] = (existing + " form-control").strip()
        if name in DATE_TIME_FIELDS:
            widget.input_type = "datetime-local"
            widget.format = "%Y-%m-%dT%H:%M"
        elif name in DATE_FIELDS:
            widget.input_type = "date"
            widget.format = "%Y-%m-%d"
        if isinstance(widget, forms.ClearableFileInput):
            widget.attrs["class"] = "form-control-file"

class ManagerForm(forms.ModelForm):
    """Part-A — complaint intake."""

    class Meta:
        model = DirectCall
        fields = [
            "date_of_complaint", "request_received_timestamp","complaint_raised_from_location", "customer_raised_issue",
            "complaint_raised", "complaint_raised_by", "contact_number", "customer_mail_id",
            "vehicle_avl_in_workshop", "complaint_raised_through",
            "vin", "psn", "complaint_assigned_to","call_type", "ialert_ticket_no", "ialert_remarks",
            "upload_file"
        ]
        widgets = {
            "customer_raised_issue": forms.Textarea(attrs={"rows": 1}),
            "ialert_remarks": forms.Textarea(attrs={"rows": 1}),
        }

    def __init__(self, *args, engineer_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        for name in PART_A_MANDATORY_FIELDS:
            if name in self.fields:
                self.fields[name].required = True

        # complaint_assigned_to becomes a dropdown of real engineer accounts
        # (+ "Others") instead of free text — REQ: "mention engineer name".
        choices = [("", "Please Select")] + list(engineer_choices or []) + [("others", "Others")]
        self.fields["complaint_assigned_to"] = forms.ChoiceField(choices=choices, required=True)

        _apply_uniform_widget_style(self)

    def clean_vin(self):
        vin = (self.cleaned_data.get("vin") or "").upper()
        return vin

    def clean_psn(self):
        return (self.cleaned_data.get("psn") or "").strip()

class EngineerForm(forms.ModelForm):
    """
    Part-B — engineer resolution, plus the unified follow-up block and the
    FIR sub-fields.

    `role` ("admin" or "engineer") decides:
      - whether the three FIR closure statuses are selectable

    Follow-Up Remark/Comment never lock, for either access level — not on
    first submission, and not under the whole-form engineer-level lock
    below. Every other field-level lock in this form skips them.
    """

    # The FIR flow fields are exempt from the whole-form engineer lock — they
    # carry their own fill-once lock instead (see __init__).
    NEVER_LOCKED_FIELDS = ("follow_up_remark", "follow_up_comment") + tuple(FIR_FLOW_FIELDS)

    class Meta:
        model = DirectCall
        # Exactly the fields engineer_form.html renders — a field in here that
        # isn't on the page would be blanked on every save.
        fields = [
            "al_updated_contact_no","follow_up_remark", "follow_up_comment","next_follow_up_exp_date",
            "call_status", 
            "date_of_closure",
            "end_customer_mail_id", "veh_reg_no", "vehicle_type", "engine_type",
            "activation_start_date", "activation_end_date", "vehicle_sale_date",
            "first_communication_in_darby", "last_communication_in_darby",
            "S_trigger_date", "s_trigger_completion_date", "C_trigger_date", "c_trigger_completion_date",
            "kilometers_hours", "main_battery_voltage",
            "vehicle_running_location", "state", "device_model", "telco_status",
            "active_profile", "nrd_category", "card_status",
            "exist_software", "updated_software", "al_mfg_plant",
            "dealer_name", "veh_model", "issue_identified", "issue_analysis",
            "Latency_7_days", "V_packet_7_days", "Latency_3_months", "V_packet_3_months",
            "upload_file_01", "remarks",
            "external_modification", "device_IMEI", "device_ICCID", "device_to_be_sent",
            "dealer_address", "engineer_recommendation", "chargable_or_not",
            "payment_status", "hod_comment",
        ] + FIR_FLOW_FIELDS
        widgets = {
            "remarks": forms.Textarea(attrs={"rows": 1}),
            "external_modification": forms.Textarea(attrs={"rows": 1}),
            "dealer_address": forms.Textarea(attrs={"rows": 1}),
            "hod_comment": forms.Textarea(attrs={"rows": 1}),
            "al_updated_contact_no": forms.Textarea(attrs={"rows": 1}),
            "follow_up_comment": forms.Textarea(attrs={"rows": 1}),
            "issue_analysis" : forms.Textarea(attrs={"rows": 1}),
            "Latency_7_days": forms.Textarea(attrs={"rows": 1}),
            "V_packet_7_days": forms.Textarea(attrs={"rows": 1}),
            "Latency_3_months": forms.Textarea(attrs={"rows": 1}),
            "V_packet_3_months": forms.Textarea(attrs={"rows": 1}),
        }

    def __init__(self, *args, role="engineer", call_type=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.role = role
        instance = kwargs.get("instance") or getattr(self, "instance", None)
        call_type = call_type or (instance.call_type if instance and instance.pk else None)

        # call_status choices — FIR closure values only for admin role
        status_choices = list(CALL_STATUS_CHOICES)
        if role != "admin":
            # An engineer can't pick a FIR closure status, but a call an admin
            # already moved to one must keep validating (the field is locked
            # to its saved value).
            current = (instance.call_status if instance and instance.pk else None)
            status_choices = [
                (v, l) for v, l in status_choices if v not in FIR_CLOSURE_STATUSES or v == current
            ]
        self.fields["call_status"] = forms.ChoiceField(choices=status_choices, required=True)

        # hod_comment is only visible to the manager/admin role
        if role != "admin" and "hod_comment" in self.fields:
            del self.fields["hod_comment"]

        # follow_up_remark — selectable list, with auto-fill wired to comment
        self.fields["follow_up_remark"] = forms.ChoiceField(
            choices=remark_choices_for(call_type), required=False,
            widget=forms.Select(attrs={
                "data-autofill-target": "#id_follow_up_comment",
                "data-autofill-map": json.dumps(REMARK_COMMENT_MAP),
            }),
        )

        # Whole-form lock for engineer-level access: once a call leaves
        # Pending, only admins may keep editing most fields — engineers get
        # a read-only view otherwise. Follow-Up Remark/Comment are exempt
        # from this (and every other lock in this form) at all times.
        #
        # Once the call is in a FIR closure status (FIR-Repair / FIR-Replace /
        # FIR-Replace_Repair) the whole form is read-only for EVERY role —
        # including Follow-Up Remark/Comment and Call Status. Only the
        # faulty-device / replacement follow-through fields stay editable,
        # and each of those locks once it is filled.
        self.in_fir_flow = bool(
            instance and instance.pk and (instance.call_status or "") in FIR_CLOSURE_STATUSES
        )
        self.never_locked = set(FIR_FLOW_FIELDS) if self.in_fir_flow else set(self.NEVER_LOCKED_FIELDS)

        self.locked_for_role = bool(
            self.in_fir_flow
            or (
                role != "admin" and instance and instance.pk
                and (instance.call_status or "Pending") != "Pending"
            )
        )
        if self.locked_for_role:
            for name, field in self.fields.items():
                if name in self.never_locked:
                    continue
                field.disabled = True

        # Fill-once lock: a FIR flow field that already holds a value is
        # disabled, so neither the page nor a crafted POST can change it.
        self.fir_flow_open = False
        if instance and instance.pk:
            for name in FIR_FLOW_FIELDS:
                if name not in self.fields:
                    continue
                value = getattr(instance, name)
                # "Working" is final only when it is Yes; a "No" can still be corrected.
                filled = (value == "Yes") if name == "new_device_working" else value not in (None, "")
                if filled:
                    self.fields[name].disabled = True
                elif (instance.call_status or "") in FIR_CLOSURE_STATUSES:
                    self.fir_flow_open = True

        _apply_uniform_widget_style(self)

    def clean(self):
        cleaned = super().clean()
        instance = self.instance

        # The FIR flow fields only take effect while the call is in a FIR
        # closure status; otherwise whatever was posted is dropped.
        status_now = (cleaned.get("call_status") or "").strip()
        if status_now not in FIR_CLOSURE_STATUSES:
            for name in FIR_FLOW_FIELDS:
                if name in cleaned:
                    cleaned[name] = getattr(instance, name)

        # Whole-form lock backend safety net — a crafted POST can't resurrect
        # disabled fields, so every field except Follow-Up Remark/Comment
        # (never locked) snaps back to its saved value.
        if getattr(self, "locked_for_role", False):
            for name in self.fields:
                if name in self.never_locked:
                    continue
                cleaned[name] = getattr(instance, name)
            return cleaned

        if not (cleaned.get("call_status") or "").strip():
            self.add_error("call_status", "Call Status is required.")

        status = (cleaned.get("call_status") or "").strip()

        # Every status except Pending needs the diagnosis details filled in.
        if status != "Pending":
            for name, label in NON_PENDING_MANDATORY_FIELDS:
                value = cleaned.get(name)
                missing = value is None or (isinstance(value, str) and not value.strip())
                # Main Battery Voltage defaults to 0 — a 0 reading is "not entered".
                if name == "main_battery_voltage" and value == 0:
                    missing = True
                if missing:
                    self.add_error(name, f"{label} is required when Call Status is {status}.")

        # FIR statuses additionally need the device-dispatch details.
        if status in FIR_MANDATORY_STATUSES:
            if not (cleaned.get("device_to_be_sent") or "").strip():
                self.add_error("device_to_be_sent", f"Required when Call Status is {status}.")
            if not (cleaned.get("dealer_address") or "").strip():
                self.add_error("dealer_address", f"Required when Call Status is {status}.")
            if (cleaned.get("engineer_recommendation") or "--") in ("", "--"):
                self.add_error("engineer_recommendation", f"Required when Call Status is {status}.")

        return cleaned


class PlantForm(forms.ModelForm):
    """What a plant login (Hyderabad / Goa) fills in for a call whose device
    was sent to their plant. Nothing else on the call is editable here.

    * Each field locks as soon as it holds a value (Plant Status only locks
      once it is Closed, so Pending can still be moved to Closed).
    * Setting Plant Status to Closed requires the CoPQ, analysis, conclusion
      and shipping fields.
    """

    class Meta:
        model = DirectCall
        fields = PLANT_EDIT_KEYS
        widgets = {
            "plant_analysis": forms.Textarea(attrs={"rows": 3}),
            "plant_conclusion": forms.Textarea(attrs={"rows": 3}),
            "device_shipped_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance
        # The plant only ever chooses Pending or Closed; "Not Applicable" is
        # set automatically for calls that aren't FIR repair/replace cases.
        self.fields["plant_status"].choices = [("Pending", "Pending"), ("Closed", "Closed")]
        if instance and instance.pk:
            for name, field in self.fields.items():
                value = getattr(instance, name)
                locked = (value == "Closed") if name == "plant_status" else value not in (None, "")
                if locked:
                    field.disabled = True
        _apply_uniform_widget_style(self)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("plant_status") == "Closed":
            for name in PLANT_REQUIRED_WHEN_CLOSED:
                value = cleaned.get(name)
                if value is None or (isinstance(value, str) and not value.strip()):
                    self.add_error(name, f"{PLANT_LABELS[name]} is required when Plant Status is Closed.")
        return cleaned

# =============================================================================
# crsc_calls — forms.py
# =============================================================================
import json

from django import forms

from .constants import remark_choices_for, REMARK_COMMENT_MAP, ALL_REMARKS
from .models import DirectCall, CALL_STATUS_CHOICES, FIR_CLOSURE_STATUSES

PART_A_MANDATORY_FIELDS = ["vin", "contact_number", "complaint_assigned_to", "call_type"]
PART_A_MANDATORY_LABELS = {
    "vin": "VIN",
    "contact_number": "Contact Number",
    "complaint_assigned_to": "Engineer Responsible",
    "call_type": "Call Type",
}

DATE_TIME_FIELDS = {
    "date_of_complaint", "request_received_timestamp",
    "activation_start_date", "activation_end_date", "first_communication_in_darby",
    "last_communication_in_darby", "S_trigger_date", "s_trigger_completion_date",
    "C_trigger_date", "date_of_closure",
}
DATE_FIELDS = {"vehicle_sale_date"}


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
            "date_of_complaint", "complaint_raised_from_location", "customer_raised_issue",
            "complaint_raised", "complaint_raised_by", "contact_number", "customer_mail_id",
            "vehicle_avl_in_workshop", "complaint_raised_through",
            "vin", "psn", "complaint_assigned_to", "ialert_remarks",
            "upload_file", "call_type", "ialert_ticket_no",
            "updated_contact_no", "request_received_timestamp",
        ]
        widgets = {
            "customer_raised_issue": forms.Textarea(attrs={"rows": 2}),
            "ialert_remarks": forms.Textarea(attrs={"rows": 2}),
            "updated_contact_no": forms.Textarea(attrs={"rows": 1}),
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
      - whether hod_comment is shown at all

    Follow-Up Remark/Comment never lock, for either access level — not on
    first submission, and not under the whole-form engineer-level lock
    below. Every other field-level lock in this form skips them.
    """

    NEVER_LOCKED_FIELDS = ("follow_up_remark", "follow_up_comment")

    class Meta:
        model = DirectCall
        fields = [
            "end_customer_mail_id", "veh_reg_no", "region", "vehicle_type",
            "vehicle_running_location", "state", "device_model", "telco_status",
            "active_profile", "activation_start_date", "activation_end_date",
            "vehicle_sale_date", "first_communication_in_darby", "last_communication_in_darby",
            "S_trigger_date", "s_trigger_completion_date", "C_trigger_date",
            "vehicle_run_kilometers", "kilometers_hours", "main_battery_voltage",
            "veh_model", "engine_type",
            "call_status", "date_of_closure",
            "contact_person_name", "contact_person_number",
            "contact_category", "exist_software", "updated_software", "issue_identified",
            "issue_description", "issue_analysis", "issue_category", "dealer_name", "al_mfg_plant",
            "call_closure_category", "nrd_category", "card_status",
            "Latency_7_days", "V_packet_7_days", "Latency_3_months", "V_packet_3_months",
            "final_analysis", "finalised_issue_category", "upload_file_01",
            "engineer_recommendation", "hod_comment", "chargable_or_not", "payment_status",
            "remarks",
            "external_modification", "device_IMEI", "device_ICCID", "device_to_be_sent",
            "dealer_address",
            "follow_up_remark", "follow_up_comment",
            "al_updated_contact_no",
        ]
        widgets = {
            "issue_category": forms.Textarea(attrs={"rows": 1}),
            "issue_description": forms.Textarea(attrs={"rows": 1}),
            "final_analysis": forms.Textarea(attrs={"rows": 1}),
            "hod_comment": forms.Textarea(attrs={"rows": 1}),
            "remarks": forms.Textarea(attrs={"rows": 1}),
            "external_modification": forms.Textarea(attrs={"rows": 1}),
            "dealer_address": forms.Textarea(attrs={"rows": 1}),
            "al_updated_contact_no": forms.Textarea(attrs={"rows": 1}),
            "follow_up_comment": forms.Textarea(attrs={"rows": 1}),
        }

    def __init__(self, *args, role="engineer", call_type=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.role = role
        instance = kwargs.get("instance") or getattr(self, "instance", None)
        call_type = call_type or (instance.call_type if instance and instance.pk else None)

        # call_status choices — FIR closure values only for admin role
        status_choices = list(CALL_STATUS_CHOICES)
        if role != "admin":
            status_choices = [(v, l) for v, l in status_choices if v not in FIR_CLOSURE_STATUSES]
        self.fields["call_status"] = forms.ChoiceField(choices=status_choices, required=True)

        # hod_comment only visible to the manager/admin role
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
        self.locked_for_role = (
            role != "admin" and instance and instance.pk
            and (instance.call_status or "Pending") != "Pending"
        )
        if self.locked_for_role:
            for name, field in self.fields.items():
                if name in self.NEVER_LOCKED_FIELDS:
                    continue
                field.disabled = True

        _apply_uniform_widget_style(self)

    def clean(self):
        cleaned = super().clean()
        instance = self.instance

        # Whole-form lock backend safety net — a crafted POST can't resurrect
        # disabled fields, so every field except Follow-Up Remark/Comment
        # (never locked) snaps back to its saved value.
        if getattr(self, "locked_for_role", False):
            for name in self.fields:
                if name in self.NEVER_LOCKED_FIELDS:
                    continue
                cleaned[name] = getattr(instance, name)
            return cleaned

        if not (cleaned.get("call_status") or "").strip():
            self.add_error("call_status", "Call Status is required.")

        # FIR — For approval sub-fields become mandatory
        if cleaned.get("call_status") == "FIR - For approval":
            if not (cleaned.get("device_to_be_sent") or "").strip():
                self.add_error("device_to_be_sent", "Required when Call Status is FIR - For approval.")
            if not (cleaned.get("dealer_address") or "").strip():
                self.add_error("dealer_address", "Required when Call Status is FIR - For approval.")
            if (cleaned.get("engineer_recommendation") or "--") in ("", "--"):
                self.add_error("engineer_recommendation", "Required when Call Status is FIR - For approval.")

        return cleaned

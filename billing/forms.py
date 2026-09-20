from django import forms
from .models import BillingData, OrderDetail


class BillingDataForm(forms.ModelForm):
    class Meta:
        model = BillingData
        exclude = ["unique_id"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["invoice_value_without_gst"].widget.attrs["readonly"] = True
        for field in self.fields.values():
            existing = field.widget.attrs.get("class", "")
            if "form-control" not in existing:
                field.widget.attrs["class"] = (existing + " form-control").strip()


class OrderDetailForm(forms.ModelForm):
    class Meta:
        model = OrderDetail
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"

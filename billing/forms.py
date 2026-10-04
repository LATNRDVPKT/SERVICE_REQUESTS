from django import forms
from .constants import (
    CUSTOMER_NAME_SUGGESTIONS, LOCATION_SUGGESTIONS, PART_NO_SUGGESTIONS,
    PRODUCT_SUGGESTIONS, CATEGORY_SUGGESTIONS, PART_SUB_CATEGORY_SUGGESTIONS,
    ITEM_SUB_CATEGORY_SUGGESTIONS,
)
from .models import BillingData, OrderDetail

# field name -> (datalist id, suggestion list) — these stay free-typed
# CharFields; the datalist is just a quick-pick, any value can be typed.
SUGGESTION_FIELDS = {
    "customer_name": ("customer_name_list", CUSTOMER_NAME_SUGGESTIONS),
    "location": ("location_list", LOCATION_SUGGESTIONS),
    "part_no": ("part_no_list", PART_NO_SUGGESTIONS),
    "product": ("product_list", PRODUCT_SUGGESTIONS),
    "category": ("category_list", CATEGORY_SUGGESTIONS),
    "part_sub_category": ("part_sub_category_list", PART_SUB_CATEGORY_SUGGESTIONS),
    "item_sub_category": ("item_sub_category_list", ITEM_SUB_CATEGORY_SUGGESTIONS),
}


# Fields shown on the invoice form, in display order (6 per row).
# Other model fields are kept on the record untouched — they just aren't
# edited from this form.
INVOICE_FORM_FIELDS = [
    "customer_name", "location", "part_no", "qty", "invoice_no", "invoice_date",
    "product", "category", "part_sub_category", "item_sub_category", "docket_no", "date_of_shipment",
    "transporter_name", "theoretical_payment_due_date", "grn_no", "actual_grn_delivery_date",
    "due_date", "total_invoice_value_with_gst",
    "invoice_value_without_gst", "credited_amount", "tds_amount", "gap", "received_date", "payment_status",
    "remarks",
]


class BillingDataForm(forms.ModelForm):
    class Meta:
        model = BillingData
        fields = INVOICE_FORM_FIELDS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field, forms.DateField):
                field.widget = forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})
        self.fields["invoice_value_without_gst"].widget.attrs["readonly"] = True
        self.fields["gap"].widget.attrs["readonly"] = True
        for name, (list_id, _suggestions) in SUGGESTION_FIELDS.items():
            if name in self.fields:
                self.fields[name].widget.attrs["list"] = list_id
        for field in self.fields.values():
            if isinstance(field.widget, forms.ClearableFileInput):
                field.widget.attrs["class"] = "form-control-file"
                continue
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

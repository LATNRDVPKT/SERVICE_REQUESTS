# =============================================================================
# billing — services/history.py
# Field-level "old value -> new value" audit trail, written on every save
# where a tracked field actually changed. Powers the eye icon.
# =============================================================================
from billing.models import BillingDataHistory

FIELD_LABELS = {
    "invoice_no": "Invoice No", "invoice_date": "Invoice Date", "product": "Product",
    "qty": "Qty", "customer_name": "Customer Name", "location": "Location",
    "invoice_value_without_gst": "Invoice Value (w/o GST)",
    "total_invoice_value_with_gst": "Total Invoice Value (w/ GST)",
    "credited_amount": "Credited Amount", "tds_amount": "TDS Amount", "gap": "Gap",
    "theoretical_payment_due_date": "Theoretical Payment Due Date", "grn_no": "GRN No",
    "actual_grn_delivery_date": "Actual GRN Delivery Date", "due_date": "Due Date",
    "payment_status": "Payment Status", "received_date": "Received Date",
    "transporter_name": "Transporter Name", "docket_no": "Docket No",
    "date_of_shipment": "Date of Shipment",
}


def diff_and_record(instance, previous, changed_by=""):
    """
    Compares `instance` (about to be saved) against `previous` (the record's
    prior state, or None for a new record) for every field in
    BillingData.TRACKED_FIELDS, and writes one BillingDataHistory row per
    field that actually changed.
    """
    if previous is None:
        return  # nothing to diff for a brand-new record

    rows = []
    for field in instance.TRACKED_FIELDS:
        old_value = getattr(previous, field, None)
        new_value = getattr(instance, field, None)
        if old_value != new_value:
            rows.append(BillingDataHistory(
                record=instance,
                unique_id=instance.unique_id,
                field_name=field,
                field_label=FIELD_LABELS.get(field, field),
                old_value=str(old_value) if old_value is not None else "",
                new_value=str(new_value) if new_value is not None else "",
                changed_by=changed_by,
            ))
    if rows:
        BillingDataHistory.objects.bulk_create(rows)

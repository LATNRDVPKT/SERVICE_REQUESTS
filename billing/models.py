# =============================================================================
# billing — models.py
# Grounded in the original BillingData / OrderDetail models. Adds
# BillingDataHistory for the eye-icon "old value -> new value" audit trail.
# =============================================================================
from django.db import models
from django.utils.timezone import now

PAYMENT_STATUS_CHOICES = [("Pending", "Pending"), ("Received", "Received")]


class OrderDetail(models.Model):
    group_name = models.CharField(max_length=100)
    item_sub_category = models.CharField(max_length=100)
    part_sub_category = models.CharField(max_length=100)
    category = models.CharField(max_length=100)
    part_no = models.CharField(max_length=100)
    po_no = models.CharField(max_length=100)
    po_date = models.DateField()
    customer_name = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    vendor_code = models.CharField(max_length=100)
    customer_code = models.CharField(max_length=100)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    gst = models.CharField(max_length=10)
    freight_scope = models.CharField(max_length=100)
    freight_scope_value = models.CharField(max_length=100)
    transporter_name = models.CharField(max_length=100)
    contact_person_name = models.CharField(max_length=100)
    contact_details = models.CharField(max_length=100)
    contact_mail_id = models.EmailField()
    engineer = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.po_no} - {self.customer_name}"


class BillingData(models.Model):
    PAYMENT_STATUS_CHOICES = PAYMENT_STATUS_CHOICES

    unique_id = models.CharField(max_length=30, unique=True, null=True, blank=True, editable=False)
    invoice_no = models.CharField(max_length=50, null=True, blank=True)
    invoice_date = models.DateField(null=True, blank=True)
    product = models.CharField(max_length=100, null=True, blank=True)
    qty = models.IntegerField(null=True, blank=True)
    category = models.CharField(max_length=100, null=True, blank=True)
    part_sub_category = models.CharField(max_length=100, null=True, blank=True)
    item_sub_category = models.CharField(max_length=100, null=True, blank=True)
    part_no = models.CharField(max_length=100, null=True, blank=True)
    customer_name = models.CharField(max_length=100, null=True, blank=True)
    location = models.CharField(max_length=100, null=True, blank=True)
    invoice_value_without_gst = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    total_invoice_value_with_gst = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    credited_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, null=True, blank=True)
    tds_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0, null=True, blank=True)
    gap = models.DecimalField(max_digits=15, decimal_places=2, default=0, null=True, blank=True)
    theoretical_payment_due_date = models.DateField(null=True, blank=True)
    grn_no = models.CharField(max_length=100, null=True, blank=True)
    actual_grn_delivery_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    payment_status = models.CharField(max_length=100, choices=PAYMENT_STATUS_CHOICES, null=True, blank=True)
    received_date = models.DateField(null=True, blank=True)
    transporter_name = models.CharField(max_length=100, null=True, blank=True)
    docket_no = models.CharField(max_length=100, null=True, blank=True)
    date_of_shipment = models.DateField(null=True, blank=True)
    due_emails = models.TextField(blank=True, null=True)
    shipment_emails = models.TextField(blank=True, null=True)
    group_name = models.CharField(max_length=100, null=True, blank=True)
    po_no = models.CharField(max_length=100, null=True, blank=True)
    po_date = models.DateField(null=True, blank=True)
    vendor_code = models.CharField(max_length=100, null=True, blank=True)
    customer_code = models.CharField(max_length=100, null=True, blank=True)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    gst = models.CharField(max_length=10, null=True, blank=True)
    freight_scope = models.CharField(max_length=100, null=True, blank=True)
    freight_scope_value = models.CharField(max_length=100, null=True, blank=True)
    contact_person_name = models.CharField(max_length=100, null=True, blank=True)
    contact_details = models.CharField(max_length=100, null=True, blank=True)
    contact_mail_id = models.EmailField(null=True, blank=True)
    engineer = models.CharField(max_length=100, null=True, blank=True)
    order = models.ForeignKey(OrderDetail, on_delete=models.SET_NULL, null=True, blank=True)

    # Fields tracked for the eye-icon change history (see services/history.py)
    TRACKED_FIELDS = [
        "invoice_no", "invoice_date", "product", "qty", "customer_name", "location",
        "invoice_value_without_gst", "total_invoice_value_with_gst", "credited_amount",
        "tds_amount", "gap", "theoretical_payment_due_date", "grn_no",
        "actual_grn_delivery_date", "due_date", "payment_status", "received_date",
        "transporter_name", "docket_no", "date_of_shipment",
    ]

    def __str__(self):
        return self.invoice_no or "No Invoice Number"

    def get_email_mapping(self):
        """
        Customer/location -> (due_emails, shipment_emails). Left empty by
        default — fill in EMAIL_MAPPING in services/due_date.py for your
        own customer/location combinations.
        """
        from .services.due_date import EMAIL_MAPPING
        return EMAIL_MAPPING.get((self.customer_name, self.location), ("", ""))

    def save(self, *args, **kwargs):
        from .services.due_date import calculate_theoretical_payment_due_date

        if not self.unique_id:
            current = now()
            prefix = f"DTILBL-{current.strftime('%y%m')}"
            last = (
                BillingData.objects.filter(unique_id__startswith=prefix)
                .order_by("-unique_id").values("unique_id").first()
            )
            next_num = 1001
            if last and last["unique_id"][-4:].isdigit():
                next_num = int(last["unique_id"][-4:]) + 1
            while True:
                candidate = f"{prefix}{next_num:04d}"
                if not BillingData.objects.filter(unique_id=candidate).exists():
                    self.unique_id = candidate
                    break
                next_num += 1

        self.theoretical_payment_due_date = calculate_theoretical_payment_due_date(
            self.invoice_date, self.location, self.item_sub_category
        ) or self.theoretical_payment_due_date

        if not self.due_emails or not self.shipment_emails:
            due_emails, shipment_emails = self.get_email_mapping()
            self.due_emails = self.due_emails or due_emails
            self.shipment_emails = self.shipment_emails or shipment_emails

        super().save(*args, **kwargs)


class BillingDataHistory(models.Model):
    """Append-only field-level audit trail — powers the eye icon."""
    record = models.ForeignKey(BillingData, on_delete=models.CASCADE, related_name="history")
    unique_id = models.CharField(max_length=30, db_index=True)
    field_name = models.CharField(max_length=100)
    field_label = models.CharField(max_length=150)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    changed_by = models.CharField(max_length=150, blank=True, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]
        indexes = [models.Index(fields=["unique_id"]), models.Index(fields=["-changed_at"])]

    def __str__(self):
        return f"{self.unique_id} — {self.field_name} changed"

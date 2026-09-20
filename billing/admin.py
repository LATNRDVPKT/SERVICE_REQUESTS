from django.contrib import admin
from .models import BillingData, OrderDetail, BillingDataHistory


@admin.register(BillingData)
class BillingDataAdmin(admin.ModelAdmin):
    list_display = ("unique_id", "invoice_no", "customer_name", "location", "payment_status", "due_date")
    search_fields = ("unique_id", "invoice_no", "customer_name", "grn_no")
    list_filter = ("payment_status", "location")
    readonly_fields = ("unique_id",)


@admin.register(OrderDetail)
class OrderDetailAdmin(admin.ModelAdmin):
    list_display = ("po_no", "customer_name", "location", "vendor_code")
    search_fields = ("po_no", "customer_name")


@admin.register(BillingDataHistory)
class BillingDataHistoryAdmin(admin.ModelAdmin):
    list_display = ("unique_id", "field_label", "old_value", "new_value", "changed_by", "changed_at")
    search_fields = ("unique_id",)
    date_hierarchy = "changed_at"

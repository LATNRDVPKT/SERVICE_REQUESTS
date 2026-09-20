from django.contrib import admin
from .models import DirectCall, DirectCallUpdate


@admin.register(DirectCall)
class DirectCallAdmin(admin.ModelAdmin):
    list_display = ("unique_id", "vin", "complaint_assigned_to", "call_type", "call_status", "date_of_complaint")
    search_fields = ("unique_id", "vin", "psn", "complaint_assigned_to")
    list_filter = ("call_status", "call_type")
    readonly_fields = ("unique_id",)
    date_hierarchy = "date_of_complaint"


@admin.register(DirectCallUpdate)
class DirectCallUpdateAdmin(admin.ModelAdmin):
    list_display = ("unique_id", "follow_up_level", "remark", "responsibility", "event_datetime")
    search_fields = ("unique_id", "vin_no")
    list_filter = ("source_field", "responsibility")
    date_hierarchy = "event_datetime"

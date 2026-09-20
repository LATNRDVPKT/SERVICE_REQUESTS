from django.contrib import admin
from .models import AIS140Request, AIS140RequestUpdate


@admin.register(AIS140Request)
class AIS140RequestAdmin(admin.ModelAdmin):
    list_display = (
        "unique_id", "vin_no", "customer_name", "state", "completion_status",
        "Update_to_AL_API", "assigned_engineer_email", "attending_engineer", "date_of_request",
    )
    search_fields = ("unique_id", "vin_no", "customer_name", "request_id", "psn")
    list_filter = ("completion_status", "state", "ticket_through", "Update_to_AL_API")
    readonly_fields = ("unique_id",)
    date_hierarchy = "date_of_request"


@admin.register(AIS140RequestUpdate)
class AIS140RequestUpdateAdmin(admin.ModelAdmin):
    list_display = ("unique_id", "source_field", "latest_remark", "attending_engineer",
                     "responsibility", "remark_datetime")
    search_fields = ("unique_id", "vin_no")
    list_filter = ("source_field", "responsibility")
    date_hierarchy = "remark_datetime"

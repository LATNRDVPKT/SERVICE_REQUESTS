from django.urls import path
from . import views
from .api_views import CRSCTicketIntakeAPIView

urlpatterns = [
    path("create_ticket/", views.manager_form, name="crsc_manager_form"),
    path("ticket_update/<int:call_id>/", views.manager_form, name="crsc_manager_form_edit"),
    path("engineer_remarks_update/<int:call_id>/", views.engineer_form, name="crsc_engineer_form"),

    path("feedback/<str:token>/", views.customer_feedback, name="crsc_feedback"),

    path("real_time_page/", views.real_time_page, name="crsc_real_time_page"),
    path("real_time_page/<int:call_id>/history/", views.call_history_partial, name="crsc_call_history_partial"),

    path("export/", views.export_page, name="crsc_export_page"),
    path("download-csv/", views.download_csv, name="crsc_download_csv"),

    path("plant/", views.plant_dashboard, name="crsc_plant_dashboard"),
    path("plant/download-csv/", views.plant_download_csv, name="crsc_plant_download_csv"),
    path("plant/<int:call_id>/", views.plant_form, name="crsc_plant_form"),

    path("api/create-ticket/", CRSCTicketIntakeAPIView.as_view(), name="crsc_api_create_ticket"),
]

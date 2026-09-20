from django.urls import path
from . import views

urlpatterns = [
    path("part_a_form/", views.part_a_form, name="part_a_form"),
    path("part_a_form/<int:ticket_id>/", views.part_a_form, name="part_a_form_edit"),
    path("part_b_form/<int:ticket_id>/", views.part_b_form, name="part_b_form"),
    path("success/", views.success_page, name="success_page"),

    path("export/", views.export_page, name="export_page"),
    path("export/download/", views.download_csv, name="download_csv"),

    path("real_time_page/", views.real_time_page, name="real_time_page"),
    path("real_time_page/<int:ticket_id>/history/", views.ticket_history_partial,
         name="ticket_history_partial"),

    path("api/create-ais140-ticket/", views.api_create_ais140_ticket, name="api_create_ais140_ticket"),
    path("api/update-ais140-remarks/", views.api_update_ais140_remarks, name="api_update_ais140_remarks"),

    path("fetch_darby_communication_ais140/<int:ticket_id>/",
         views.fetch_darby_communication_ais140, name="fetch_darby_communication_ais140"),
]

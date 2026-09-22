from django.urls import path
from . import views

urlpatterns = [
    path("manager_form/", views.manager_form, name="crsc_manager_form"),
    path("manager_form/<int:call_id>/", views.manager_form, name="crsc_manager_form_edit"),
    path("engineer_form/<int:call_id>/", views.engineer_form, name="crsc_engineer_form"),

    path("real_time_page/", views.real_time_page, name="crsc_real_time_page"),
    path("real_time_page/<int:call_id>/history/", views.call_history_partial, name="crsc_call_history_partial"),

    path("export/", views.export_page, name="crsc_export_page"),
    path("download-csv/", views.download_csv, name="crsc_download_csv"),
]

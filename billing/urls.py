from django.urls import path
from . import views

urlpatterns = [
    path("add/", views.add_billing_data, name="billing_add"),
    path("add/<int:pk>/", views.add_billing_data, name="billing_add_detail"),
    path("real_time/", views.real_time_page, name="billing_real_time_page"),
    path("real_time/<int:pk>/history/", views.record_history_partial, name="billing_record_history_partial"),
    path("export/", views.export_page, name="billing_export_page"),
    path("download-csv/", views.download_csv, name="billing_download_csv"),
]

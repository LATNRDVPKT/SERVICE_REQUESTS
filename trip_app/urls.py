from django.urls import path
from . import views

app_name = "trip_app"

urlpatterns = [
    path("", views.upload_file, name="upload"),
]

from django.urls import path
from . import views

urlpatterns = [
    path("", views.search_page, name="data_search"),
    path("api/fetch/", views.fetch_external_data, name="data_search_fetch"),
]

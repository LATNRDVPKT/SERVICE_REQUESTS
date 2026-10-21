from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("accounts/", include("accounts.urls")),
    path("ais140/", include("ais140_requests.urls")),
    path("crsc/", include("customer_requests.urls")),
    path("billing/", include("billing.urls")),
    path("data-search/", include("analysis.urls")),
    path("trip-analysis/", include("trip_analysis.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

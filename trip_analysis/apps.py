from django.apps import AppConfig


class TripAnalysisConfig(AppConfig):
    """Trip analysis — upload a trip file and download the analysed report."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "trip_analysis"
    verbose_name = "Trip Analysis"

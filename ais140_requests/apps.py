from django.apps import AppConfig


class Ais140RequestsConfig(AppConfig):
    """AIS140 certification requests (formerly "AIS140_FLOW").

    `label` keeps the original app name so the existing database tables
    (AIS140_FLOW_*) and migration history are reused unchanged.
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "ais140_requests"
    label = "AIS140_FLOW"
    verbose_name = "AIS140 Requests"

from django.apps import AppConfig


class CustomerRequestsConfig(AppConfig):
    """Customer requests (formerly "CRSC Calls").

    `label` keeps the original app name so the existing database tables
    (crsc_calls_*) and migration history are reused unchanged.
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "customer_requests"
    label = "crsc_calls"
    verbose_name = "Customer Requests"

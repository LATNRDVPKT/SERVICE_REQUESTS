from django.conf import settings
from django.db import models

ROLE_CHOICES = [
    ("admin", "Admin"),
    ("engineer", "Engineer"),
]


class UserProfile(models.Model):
    """
    One profile per Django auth User, shared across all three modules
    (AIS140, CRSC Calls, Billing). `role` decides admin-only access
    (Billing) and `display_name` is what shows up as "Engineer" wherever
    an app needs to attribute a record to a person, instead of a free-typed
    e-mail address.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="engineer")
    display_name = models.CharField(max_length=150)

    class Meta:
        ordering = ["display_name"]

    def __str__(self):
        return f"{self.display_name} ({self.role})"

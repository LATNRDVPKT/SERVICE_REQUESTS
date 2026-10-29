"""
Keeps plant and finance users inside their own pages.

- Plant users can only open /crsc/plant/
- Finance users can only open /billing/

Any other URL sends them back to their own dashboard.
"""
from django.shortcuts import redirect

PLANT_ALLOWED_PATHS = ("/crsc/plant/", "/accounts/", "/static/")
FINANCE_ALLOWED_PATHS = ("/billing/", "/accounts/", "/static/")


class RoleAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        role = get_role(request.user)
        path = request.path

        if role == "plant" and not path.startswith(PLANT_ALLOWED_PATHS):
            return redirect("crsc_plant_dashboard")

        if role == "finance" and not path.startswith(FINANCE_ALLOWED_PATHS):
            return redirect("billing_real_time_page")

        return self.get_response(request)


def get_role(user):
    """Returns the user's role, or None if they are not logged in or have no profile."""
    if not user.is_authenticated:
        return None
    profile = getattr(user, "profile", None)
    if profile is None:
        return None
    return profile.role

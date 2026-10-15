"""
Locks plant logins (role="plant") into the CRSC plant screens.

A plant user may open only /crsc/plant/..., the login/logout pages and
static files. Any other URL — the AIS140, billing and analysis modules, the
normal CRSC dashboard and forms, the history popups, admin — bounces back to
the plant dashboard, so the restriction can't be bypassed by typing a URL.
"""
from django.shortcuts import redirect

ALLOWED_PREFIXES = ("/crsc/plant/", "/accounts/", "/static/")


class PlantAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            profile = getattr(user, "profile", None)
            if profile is not None and profile.role == "plant" and not request.path.startswith(ALLOWED_PREFIXES):
                return redirect("crsc_plant_dashboard")
        return self.get_response(request)

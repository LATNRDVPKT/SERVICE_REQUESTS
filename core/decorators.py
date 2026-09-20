"""Shared access-control decorators used across the workflow apps."""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def admin_required(view_func):
    """Restricts a view to users whose profile.role == 'admin' (Billing app)."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        profile = getattr(request.user, "profile", None)
        if not profile or profile.role != "admin":
            messages.error(request, "Billing is restricted to admin users.")
            return redirect("home")
        return view_func(request, *args, **kwargs)
    return wrapper

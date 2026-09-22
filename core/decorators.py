"""Shared access-control decorators used across the workflow apps."""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def admin_required(view_func=None, *, message="This page is restricted to admin users."):
    """
    Restricts a view to users whose profile.role == 'admin'. Usable either
    bare (`@admin_required`) or with a custom flash message
    (`@admin_required(message="...")`).
    """
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(request, *args, **kwargs):
            profile = getattr(request.user, "profile", None)
            if not profile or profile.role != "admin":
                messages.error(request, message)
                return redirect("home")
            return fn(request, *args, **kwargs)
        return wrapper

    if view_func is not None:
        return decorator(view_func)
    return decorator

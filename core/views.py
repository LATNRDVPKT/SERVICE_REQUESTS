from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def home(request):
    """Landing page — links into the three workflow modules."""
    return render(request, "core/home.html")

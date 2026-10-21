# =============================================================================
# analysis — views.py
# "7 Days Analysis" — search any VIN / PSN / ICCID and see Darby's live
# asset details plus a 7-day communication/packet summary. Open to every
# logged-in user (admin or engineer), read-only, nothing is saved.
# =============================================================================
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .services.darby import (
    DarbyLookupError, fetch_asset, fetch_analytics_summary,
    build_vin_details, build_summary_table,
)

logger = logging.getLogger(__name__)

SEARCH_FIELD_CHOICES = [("vin", "VIN"), ("psn", "PSN"), ("iccid", "ICCID")]


@login_required
def search_page(request):
    search_field = request.GET.get("search_field", "vin")
    search_value = (request.GET.get("search_value") or "").strip()
    return render(request, "analysis/search_page.html", {
        "search_field": search_field,
        "search_value": search_value,
        "search_field_choices": SEARCH_FIELD_CHOICES,
    })


@login_required
@require_GET
def fetch_external_data(request):
    search_field = request.GET.get("search_field", "vin")
    search_value = (request.GET.get("search_value") or "").strip()
    if not search_value:
        return JsonResponse({"error": "Enter a VIN, PSN or ICCID to search."}, status=400)

    try:
        asset = fetch_asset(search_field, search_value)
    except DarbyLookupError as exc:
        logger.warning("Darby asset search failed for %s=%s: %s", search_field, search_value, exc)
        return JsonResponse({"error": str(exc)}, status=502)

    if not asset:
        return JsonResponse({"error": f"No asset found for {search_field.upper()}: {search_value}"}, status=404)

    vin_details = build_vin_details(asset)

    summary_table, summary_row = [], None
    asset_id = asset.get("assetId")
    if asset_id:
        try:
            analytics_data = fetch_analytics_summary(asset_id)
        except DarbyLookupError as exc:
            logger.warning("Darby analytics summary failed for asset_id=%s: %s", asset_id, exc)
            analytics_data = {}
        summary_table, summary_row = build_summary_table(analytics_data)

    return JsonResponse({
        "vin_details": vin_details,
        "summary_table": summary_table,
        "summary_row": summary_row,
    })

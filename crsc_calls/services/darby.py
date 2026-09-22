# =============================================================================
# crsc_calls — services/darby.py
# Same Darby asset-search integration pattern as AIS140_FLOW/services/darby.py,
# mapped onto CRSC Calls' Part-B vehicle/device fields. Triggered automatically
# right after a Part-A call is created (same VIN-driven lookup).
# =============================================================================
import logging

import requests
from django.conf import settings
from django.utils.timezone import now

logger = logging.getLogger(__name__)


class DarbyLookupError(Exception):
    pass


def _bearer_header(token):
    """Builds the Authorization header from DARBY_BEARER_TOKEN regardless of
    whether the configured value already includes a "Bearer " prefix (easy
    mistake when pasting a token straight from an API console) — avoids
    ever sending a malformed "Bearer Bearer ..." header, which Darby
    would reject outright."""
    token = (token or "").strip()
    if token.lower().startswith("bearer "):
        token = token[len("bearer "):].strip()
    return f"Bearer {token}"


def fetch_vehicle_data(vin):
    if not vin:
        raise DarbyLookupError("No VIN supplied for Darby lookup.")
    if not settings.DARBY_BEARER_TOKEN:
        raise DarbyLookupError("Darby credentials are not configured.")

    headers = {"Authorization": _bearer_header(settings.DARBY_BEARER_TOKEN), "Content-Type": "application/json"}
    try:
        response = requests.post(settings.DARBY_SEARCH_URL, json={"vin": vin},
                                  headers=headers, timeout=settings.DARBY_REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        raise DarbyLookupError(f"Darby request failed: {exc}") from exc

    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise DarbyLookupError(f"Darby returned HTTP {response.status_code}")

    try:
        data = response.json()
    except ValueError as exc:
        raise DarbyLookupError(f"Darby returned non-JSON response: {exc}") from exc

    record = data.get("data") or data.get("result") or data
    if not record:
        return None

    return {
        "device_model": record.get("device_model") or record.get("deviceModel"),
        "veh_model": record.get("vehicle_model") or record.get("vehicleModel"),
        "telco_status": record.get("telco_status") or record.get("telcoStatus"),
        "main_battery_voltage": record.get("main_battery_voltage") or record.get("batteryVoltage"),
        "vehicle_run_kilometers": record.get("vehicle_run_kms") or record.get("vehicleRunKms"),
        "first_communication_in_darby": record.get("first_communication") or record.get("firstCommunication"),
        "last_communication_in_darby": record.get("last_communication") or record.get("lastCommunication"),
    }


def run_darby_lookup_and_save(call):
    """
    Fetches vehicle data for `call.vin` and persists it, same orchestration
    as AIS140_FLOW's run_darby_lookup_and_save — including recording
    darby_lookup_status/darby_lookup_at so a blank Darby-sourced field can
    be told apart from "lookup never ran" vs. "ran and found nothing" vs.
    "failed". Never raises — a Darby outage never blocks call creation.
    """
    from crsc_calls.models import DirectCall

    try:
        result = fetch_vehicle_data(call.vin)
    except DarbyLookupError as exc:
        logger.warning("Darby lookup failed for call %s (%s): %s", call.unique_id, call.vin, exc)
        DirectCall.objects.filter(pk=call.pk).update(darby_lookup_status="failed", darby_lookup_at=now())
        return False

    if result is None:
        DirectCall.objects.filter(pk=call.pk).update(darby_lookup_status="not_found", darby_lookup_at=now())
        return False

    update_fields = {k: v for k, v in result.items() if v}
    update_fields["darby_lookup_status"] = "success"
    update_fields["darby_lookup_at"] = now()
    DirectCall.objects.filter(pk=call.pk).update(**update_fields)
    logger.info("Darby lookup saved for call %s (%s)", call.unique_id, call.vin)
    return True

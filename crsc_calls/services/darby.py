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


def fetch_vehicle_data(vin):
    if not vin:
        raise DarbyLookupError("No VIN supplied for Darby lookup.")
    if not settings.DARBY_BEARER_TOKEN:
        raise DarbyLookupError("Darby credentials are not configured.")

    headers = {"Authorization": f"Bearer {settings.DARBY_BEARER_TOKEN}", "Content-Type": "application/json"}
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
    from crsc_calls.models import DirectCall

    try:
        result = fetch_vehicle_data(call.vin)
    except DarbyLookupError as exc:
        logger.warning("Darby lookup failed for call %s (%s): %s", call.unique_id, call.vin, exc)
        return False

    if result is None:
        return False

    update_fields = {k: v for k, v in result.items() if v}
    if update_fields:
        DirectCall.objects.filter(pk=call.pk).update(**update_fields)
        logger.info("Darby lookup saved for call %s (%s)", call.unique_id, call.vin)
    return bool(update_fields)

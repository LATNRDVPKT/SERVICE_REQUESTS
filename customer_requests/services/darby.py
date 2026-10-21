# =============================================================================
# customer_requests — services/darby.py
# Same Darby asset-search integration pattern as ais140_requests/services/darby.py,
# mapped onto CRSC Calls' Part-B vehicle/device fields. Triggered automatically
# right after a Part-A call is created (same VIN-driven lookup).
# =============================================================================
import datetime
import logging

import requests
from django.conf import settings
from django.utils.dateparse import parse_datetime
from django.utils.timezone import now

logger = logging.getLogger(__name__)
api_logger = logging.getLogger("api_traffic")


def _parse_darby_timestamp(value):
    """Darby's real communication timestamps come back as epoch
    milliseconds (e.g. lastCommunication=1790585920000); this also accepts
    a plain ISO datetime string in case that ever changes for a given
    field."""
    if not value:
        return None
    if isinstance(value, str) and value.isdigit():
        value = int(value)
    if isinstance(value, (int, float)):
        try:
            return datetime.datetime.fromtimestamp(value / 1000, tz=datetime.timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None
    if isinstance(value, str):
        return parse_datetime(value)
    return None


def _to_int(value):
    if value in (None, ""):
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


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
    payload = {"assetType": "DEVICE", "filters": {"vin": [vin]}}

    api_logger.info("OUTGOING Darby lookup — vin=%s url=%s payload=%s", vin, settings.DARBY_SEARCH_URL, payload)
    try:
        response = requests.post(settings.DARBY_SEARCH_URL, json=payload,
                                  headers=headers, timeout=settings.DARBY_REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        api_logger.error("OUTGOING Darby lookup FAILED — vin=%s: %s", vin, exc)
        raise DarbyLookupError(f"Darby request failed: {exc}") from exc

    if response.status_code == 404:
        api_logger.info("INCOMING Darby lookup — vin=%s not found (404)", vin)
        return None
    if response.status_code != 200:
        api_logger.error(
            "INCOMING Darby lookup REJECTED — vin=%s status=%s body=%s",
            vin, response.status_code, response.text[:300],
        )
        raise DarbyLookupError(f"Darby returned HTTP {response.status_code}")

    api_logger.info(
        "INCOMING Darby lookup OK — vin=%s status=%s body=%s",
        vin, response.status_code, response.text[:500],
    )

    try:
        data = response.json()
    except ValueError as exc:
        raise DarbyLookupError(f"Darby returned non-JSON response: {exc}") from exc

    # Darby returns {"results": [ {...} ]} for the filters-based search —
    # take the first match for this VIN, if any.
    results = data.get("results") or []
    record = results[0] if results else None
    if not record:
        return None

    telco_status = record.get("cardState") or ""

    # Activation window depends on which telco status this asset is in —
    # Bootstrap and Commercial each have their own start/expiry pair.
    if telco_status == "Bootstrap":
        activation_start_ms = record.get("bootstrapActivationDate")
        activation_end_ms = record.get("bootstrapExpiryDate")
    elif telco_status == "Commercial":
        activation_start_ms = record.get("commercialActivationDate")
        activation_end_ms = record.get("commercialExpiryDate")
    else:
        activation_start_ms = None
        activation_end_ms = None

    # last_communication: Darby's two Kafka-published timestamps (V-packet /
    # A-packet) are more current than the plain lastCommunication field when
    # present — take whichever of the two is newer, falling back to
    # lastCommunication if neither Kafka timestamp is set.
    vpacket_dt = _parse_darby_timestamp(record.get("kafkaVPacketPublishedTime"))
    apacket_dt = _parse_darby_timestamp(record.get("kafkaAPacketPublishedTime"))
    if vpacket_dt and apacket_dt:
        last_communication_dt = max(vpacket_dt, apacket_dt)
    else:
        last_communication_dt = vpacket_dt or apacket_dt or _parse_darby_timestamp(record.get("lastCommunication"))

    return {
        "device_model": record.get("productCode"),
        "telco_status": telco_status,
        "exist_software": record.get("fwCategory"),
        "active_profile": record.get("profileStatus"),
        "nrd_category": record.get("nrdCategory"),
        "device_ICCID": record.get("iccid"),
        "al_mfg_plant": record.get("alMfgPlant"),
        "card_status": record.get("cardStatus"),
        "psn": record.get("assetName"),
        "main_battery_voltage": record.get("vehicleBatteryPotential"),
        "kilometers_hours": _to_int(record.get("odometer")),
        "state": record.get("state"),
        "activation_start_date": _parse_darby_timestamp(activation_start_ms),
        "activation_end_date": _parse_darby_timestamp(activation_end_ms),
        "S_trigger_date": _parse_darby_timestamp(record.get("S_activationRequestDate")),
        "C_trigger_date": _parse_darby_timestamp(record.get("C_activationRequestDate")),
        "s_trigger_completion_date": _parse_darby_timestamp(record.get("S_completionDate")),
        "c_trigger_completion_date": _parse_darby_timestamp(record.get("C_completionDate")),
        "first_communication_in_darby": _parse_darby_timestamp(record.get("firstCommunication")),
        "last_communication_in_darby": last_communication_dt,
    }


def run_darby_lookup_and_save(call):
    """
    Fetches vehicle data for `call.vin` and persists it. Never raises — a
    Darby outage never blocks call creation.
    """
    from customer_requests.models import DirectCall

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
    return True

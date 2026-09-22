# =============================================================================
# AIS140_FLOW — services/darby.py
# REQ-13 — look up device data (ICCID, IMEI, product code, architecture type,
# battery voltage) from the Darby asset-search API by VIN, and save the
# result onto the ticket. Called automatically right after a Part-A ticket
# is created (see views.part_a_form).
# =============================================================================
import logging

import requests
from django.conf import settings
from django.utils.timezone import now

logger = logging.getLogger(__name__)
api_logger = logging.getLogger("api_traffic")


class DarbyLookupError(Exception):
    """Raised on a hard failure (network/timeout/bad response) talking to Darby."""


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


def fetch_device_data(vin_no):
    """
    Query Darby for a single VIN and return a dict:
        {"iccid": "...", "imei": "...", "product_code": "...",
         "architecture_type": "...", "battery_voltage": "..."}
    Returns None if Darby has no record for this VIN.
    Raises DarbyLookupError on network/HTTP failure.
    """
    if not vin_no:
        raise DarbyLookupError("No VIN supplied for Darby lookup.")

    if not settings.DARBY_BEARER_TOKEN:
        # Not configured — treat as a soft failure so ticket creation
        # never blocks on missing Darby credentials.
        logger.warning("DARBY_BEARER_TOKEN is not set — skipping Darby lookup for %s", vin_no)
        raise DarbyLookupError("Darby credentials are not configured.")

    headers = {
        "Authorization": _bearer_header(settings.DARBY_BEARER_TOKEN),
        "Content-Type": "application/json",
    }
    payload = {"vin": vin_no}

    api_logger.info("OUTGOING Darby lookup — vin=%s url=%s", vin_no, settings.DARBY_SEARCH_URL)
    try:
        response = requests.post(
            settings.DARBY_SEARCH_URL,
            json=payload,
            headers=headers,
            timeout=settings.DARBY_REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        api_logger.error("OUTGOING Darby lookup FAILED — vin=%s: %s", vin_no, exc)
        raise DarbyLookupError(f"Darby request failed: {exc}") from exc

    if response.status_code == 404:
        api_logger.info("OUTGOING Darby lookup — vin=%s not found (404)", vin_no)
        return None
    if response.status_code != 200:
        api_logger.error(
            "OUTGOING Darby lookup REJECTED — vin=%s status=%s body=%s",
            vin_no, response.status_code, response.text[:300],
        )
        raise DarbyLookupError(f"Darby returned HTTP {response.status_code}: {response.text[:300]}")

    api_logger.info("OUTGOING Darby lookup OK — vin=%s status=%s", vin_no, response.status_code)

    try:
        data = response.json()
    except ValueError as exc:
        raise DarbyLookupError(f"Darby returned non-JSON response: {exc}") from exc

    # Darby's exact response shape should be confirmed and this extraction
    # adjusted to match it; the keys below are the placeholders agreed in
    # the specification.
    record = data.get("data") or data.get("result") or data
    if not record:
        return None

    return {
        "iccid": record.get("iccid") or record.get("ICCID"),
        "imei": record.get("imei") or record.get("IMEI"),
        "model": record.get("model") or record.get("device_model") or record.get("deviceModel"),
        "product_code": record.get("product_code") or record.get("productCode"),
        "architecture_type": record.get("architecture_type") or record.get("architectureType"),
        "battery_voltage": record.get("battery_voltage") or record.get("batteryVoltage"),
    }


def run_darby_lookup_and_save(ticket):
    """
    REQ-13 orchestration: fetch device data for `ticket.vin_no` and persist
    it onto the ticket. Never raises — logs and records lookup status
    instead, so a Darby outage never blocks ticket creation.
    """
    from AIS140_FLOW.models import AIS140Request  # local import avoids cycles

    try:
        result = fetch_device_data(ticket.vin_no)
    except DarbyLookupError as exc:
        logger.warning("Darby lookup failed for ticket %s (%s): %s", ticket.unique_id, ticket.vin_no, exc)
        AIS140Request.objects.filter(pk=ticket.pk).update(
            darby_lookup_status="failed", darby_lookup_at=now()
        )
        return False

    if result is None:
        AIS140Request.objects.filter(pk=ticket.pk).update(
            darby_lookup_status="not_found", darby_lookup_at=now()
        )
        return False

    AIS140Request.objects.filter(pk=ticket.pk).update(
        icicid_no=result.get("iccid") or ticket.icicid_no,
        imei_no=result.get("imei") or ticket.imei_no,
        device_model=result.get("model") or ticket.device_model,
        device_product_code=result.get("product_code") or ticket.device_product_code,
        device_architecture_type=result.get("architecture_type") or ticket.device_architecture_type,
        device_battery_voltage=result.get("battery_voltage") or ticket.device_battery_voltage,
        darby_lookup_status="success",
        darby_lookup_at=now(),
    )
    logger.info("Darby lookup saved for ticket %s (%s)", ticket.unique_id, ticket.vin_no)
    return True

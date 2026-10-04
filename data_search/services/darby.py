# =============================================================================
# data_search — services/darby.py
# Live "7 Days Analysis" lookup — search any VIN / PSN / ICCID against
# Darby's asset-search API, then pull that asset's last-7-days
# communication summary from Darby's analytics-daily-summary API.
#
# Unlike crsc_calls/AIS140_FLOW's Darby integrations (which save a handful
# of fields onto a ticket), this is a pure read-through: nothing is
# persisted, the page just displays whatever Darby returns right now.
# =============================================================================
import datetime
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)
api_logger = logging.getLogger("api_traffic")

# Which Darby filter key each UI search field maps to — confirmed directly
# against the real API (Darby has no "psn" filter; PSN is Darby's
# "assetName").
SEARCH_FIELD_TO_DARBY_FILTER = {
    "vin": "vin",
    "psn": "assetName",
    "iccid": "iccid",
}


class DarbyLookupError(Exception):
    pass


def _bearer_header(token):
    token = (token or "").strip()
    if token.lower().startswith("bearer "):
        token = token[len("bearer "):].strip()
    return f"Bearer {token}"


def _ms_to_iso(ms):
    if not ms:
        return ""
    try:
        return datetime.datetime.fromtimestamp(int(ms) / 1000, tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError, OSError):
        return ""


def fetch_asset(field, value):
    """
    Looks up a single Darby asset by VIN, PSN (Darby's assetName) or ICCID.
    Returns the raw asset dict, or None if nothing matched.
    Raises DarbyLookupError on a network/HTTP failure.
    """
    darby_filter_key = SEARCH_FIELD_TO_DARBY_FILTER.get(field)
    if not darby_filter_key:
        raise DarbyLookupError(f"Unknown search field: {field}")
    if not value:
        raise DarbyLookupError("No search value supplied.")
    if not settings.DARBY_BEARER_TOKEN:
        raise DarbyLookupError("Darby credentials are not configured.")

    headers = {"Authorization": _bearer_header(settings.DARBY_BEARER_TOKEN), "Content-Type": "application/json"}
    payload = {"assetType": "DEVICE", "filters": {darby_filter_key: [value]}}

    api_logger.info("OUTGOING Darby asset search — field=%s value=%s payload=%s", field, value, payload)
    try:
        response = requests.post(
            settings.DARBY_SEARCH_URL, json=payload, headers=headers, timeout=settings.DARBY_REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        api_logger.error("OUTGOING Darby asset search FAILED — value=%s: %s", value, exc)
        raise DarbyLookupError(f"Darby request failed: {exc}") from exc

    if response.status_code != 200:
        api_logger.error(
            "INCOMING Darby asset search REJECTED — value=%s status=%s body=%s",
            value, response.status_code, response.text[:300],
        )
        raise DarbyLookupError(f"Darby returned HTTP {response.status_code}")

    api_logger.info(
        "INCOMING Darby asset search OK — value=%s status=%s body=%s",
        value, response.status_code, response.text[:500],
    )

    try:
        results = response.json().get("results") or []
    except ValueError as exc:
        raise DarbyLookupError(f"Darby returned non-JSON response: {exc}") from exc

    return results[0] if results else None


def fetch_analytics_summary(asset_id, days=7):
    """
    Pulls the last `days` days of Darby's analytics-daily-summary for
    `asset_id`. Returns the raw analytics response dict (may be empty).
    Raises DarbyLookupError on a network/HTTP failure.
    """
    end_dt = datetime.datetime.now(datetime.timezone.utc)
    start_dt = end_dt - datetime.timedelta(days=days - 1)
    start_time = start_dt.strftime("%Y-%m-%dT00:00:00Z")
    end_time = end_dt.strftime("%Y-%m-%dT23:59:59Z")

    url = f"{settings.DARBY_ANALYTICS_BASE_URL}/{asset_id}/analytics-daily-summary"
    headers = {"Authorization": _bearer_header(settings.DARBY_BEARER_TOKEN), "Content-Type": "application/json"}
    params = {"startTime": start_time, "endTime": end_time}

    api_logger.info("OUTGOING Darby analytics summary — asset_id=%s url=%s params=%s", asset_id, url, params)
    try:
        response = requests.get(url, headers=headers, params=params, timeout=settings.DARBY_REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        api_logger.error("OUTGOING Darby analytics summary FAILED — asset_id=%s: %s", asset_id, exc)
        raise DarbyLookupError(f"Darby analytics request failed: {exc}") from exc

    if response.status_code != 200:
        api_logger.error(
            "INCOMING Darby analytics summary REJECTED — asset_id=%s status=%s body=%s",
            asset_id, response.status_code, response.text[:300],
        )
        raise DarbyLookupError(f"Darby analytics returned HTTP {response.status_code}")

    api_logger.info(
        "INCOMING Darby analytics summary OK — asset_id=%s status=%s body=%s",
        asset_id, response.status_code, response.text[:500],
    )

    try:
        return response.json()
    except ValueError as exc:
        raise DarbyLookupError(f"Darby analytics returned non-JSON response: {exc}") from exc


def build_vin_details(asset):
    """Flattens the raw asset dict into the exact shape the search page's
    VIN-details table expects."""
    address = (asset.get("address") or "").strip()
    state, country = "", ""
    if address:
        parts = [p.strip() for p in address.split(",") if p.strip()]
        if len(parts) >= 2:
            state = parts[-2]
        if len(parts) >= 1:
            country = parts[-1]

    activation_end_ms = (
        asset.get("latestActivityEndDate") or asset.get("commercialExpiryDate") or asset.get("bootstrapExpiryDate")
    )

    return {
        "vin": asset.get("vin", ""),
        "productSerialNumber": asset.get("productSerialNumber") or asset.get("assetName", ""),
        "productCode": asset.get("productCode", ""),
        "cardState": asset.get("cardState", ""),
        "cardStatus": asset.get("cardStatus", ""),
        "alertPacketKafkaPublishedTime": _ms_to_iso(asset.get("kafkaAlertPacketPublishedTime")),
        "vpacketKafkaPublishedTime": _ms_to_iso(asset.get("kafkaVPacketPublishedTime")),
        "apacketKafkaPublishedTime": _ms_to_iso(asset.get("kafkaAPacketPublishedTime")),
        "imei": asset.get("imei", ""),
        "ignitionStatus": asset.get("ignitionStatus", ""),
        "vehicleBatteryPotential": asset.get("vehicleBatteryPotential") or asset.get("internalBatteryPotential", ""),
        "latestCsRenewalEndDate": _ms_to_iso(activation_end_ms),
        "address": address,
        "comStatus": asset.get("comStatus", ""),
        "state": state,
        "country": country,
    }


def build_summary_table(analytics_data):
    """Flattens analytics_data["results"] into the per-day rows (+ a totals
    row) the search page's 7-day table expects."""
    rows = []
    for row in analytics_data.get("results", []):
        min_odo = row.get("min_odo", 0) or 0
        max_odo = row.get("max_odo", 0) or 0
        date_raw = row.get("date", "")
        try:
            date_fmt = datetime.datetime.strptime(date_raw, "%Y-%m-%d").strftime("%d-%m-%Y") if date_raw else ""
        except ValueError:
            date_fmt = date_raw
        rows.append({
            "date": date_fmt,
            "v_packets": row.get("v_count", 0) or 0,
            "a_packets": row.get("a_count", 0) or 0,
            "total_packets": (row.get("v_count", 0) or 0) + (row.get("a_count", 0) or 0),
            "start_odo": min_odo,
            "end_odo": max_odo,
            "kms": (max_odo - min_odo) if max_odo and min_odo else 0,
            "lat_0_5": row.get("cnt_0_5m", 0) or 0,
            "lat_5_15": row.get("cnt_5_15m", 0) or 0,
            "lat_15_30": row.get("cnt_15_30m", 0) or 0,
            "lat_30_1h": row.get("cnt_30_60m", 0) or 0,
            "lat_1h_3h": row.get("cnt_1_3h", 0) or 0,
            "lat_3h_6h": row.get("cnt_3_6h", 0) or 0,
            "lat_6h_12h": row.get("cnt_6_12h", 0) or 0,
            "lat_12_24h": row.get("cnt_12_24h", 0) or 0,
            "lat_gt_24h": row.get("cnt_gt_24h", 0) or 0,
        })

    if not rows:
        return rows, None

    latency_keys = [
        "lat_0_5", "lat_5_15", "lat_15_30", "lat_30_1h",
        "lat_1h_3h", "lat_3h_6h", "lat_6h_12h", "lat_12_24h", "lat_gt_24h",
    ]
    summary_row = {
        "date": "Summary",
        "start_odo": rows[0]["start_odo"],
        "end_odo": rows[-1]["end_odo"],
        "kms": rows[-1]["end_odo"] - rows[0]["start_odo"],
        "total_packets": sum(r["total_packets"] for r in rows),
        "a_packets": sum(r["a_packets"] for r in rows),
        "v_packets": sum(r["v_packets"] for r in rows),
    }
    for key in latency_keys:
        summary_row[key] = sum(r[key] for r in rows)

    return rows, summary_row

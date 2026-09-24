# =============================================================================
# AIS140_FLOW — services/ialert.py
# Pushes a Part-B update to iAlert for API-originated tickets
# (request_id present). The local DB is only written by the caller if this
# push succeeds — see views.part_b_form.
#
# Same token-generate-then-push flow as crsc_calls/services/ialert.py:
# generate a token from the login endpoint, then POST the update using that
# token. Separate URLs/credential from crsc's since AIS140 is a different AL
# integration (AIS140_IALERT_* settings vs CRSC_IALERT_*).
# =============================================================================
import logging

import requests
from django.conf import settings

from AIS140_FLOW.constants import IALERT_FILE_MAPPING

logger = logging.getLogger(__name__)
api_logger = logging.getLogger("api_traffic")


class IAlertPushError(Exception):
    """Raised when the iAlert token request or the update push fails."""


def _get_ialert_token():
    """Requests a fresh token from the iAlert login endpoint. Returns the
    token string, or raises IAlertPushError if the login call fails or
    returns no usable token."""
    if not settings.AIS140_IALERT_LOGIN_URL:
        raise IAlertPushError("AIS140_IALERT_LOGIN_URL is not configured.")

    headers = {"token": settings.AIS140_IALERT_LOGIN_TOKEN_HEADER_VALUE}

    try:
        response = requests.get(settings.AIS140_IALERT_LOGIN_URL, headers=headers, timeout=30)
    except requests.RequestException as exc:
        api_logger.error("iAlert (AIS140) token request FAILED: %s", exc)
        raise IAlertPushError(f"Could not reach the iAlert login endpoint: {exc}") from exc

    if response.status_code != 200:
        api_logger.error(
            "iAlert (AIS140) token request REJECTED — status=%s body=%s",
            response.status_code, response.text[:300],
        )
        raise IAlertPushError(f"iAlert login failed (HTTP {response.status_code}).")

    try:
        body = response.json()
        token = body.get("token") or body.get("access_token") or body.get("data")
    except ValueError:
        # Login endpoint returned plain text instead of JSON.
        token = response.text.strip()

    if not token:
        api_logger.error("iAlert (AIS140) token response had no usable token: %s", response.text[:300])
        raise IAlertPushError("iAlert login succeeded but returned no token.")

    return token


def push_update_to_ialert(ticket, form_files=None):
    """
    Build and send the outbound payload to iAlert for this ticket, based on
    ticket.Update_to_AL_API. Raises IAlertPushError on any non-2xx response
    or network failure — callers must not save the ticket locally if this
    raises.
    """
    if not settings.AIS140_IALERT_PUSH_URL:
        raise IAlertPushError("AIS140_IALERT_PUSH_URL is not configured.")

    token = _get_ialert_token()

    update_value = (ticket.Update_to_AL_API or "").strip()

    payload = {
        "request_id": ticket.request_id,
        "unique_id": ticket.unique_id,
        "vin_no": ticket.vin_no,
        "update_to_al_api": update_value,
        "request_remarks": ticket.request_remarks,
        "request_comments": ticket.request_comments,
        "attending_engineer": ticket.attending_engineer,
        "completion_status": ticket.completion_status,
    }

    headers = {"Authorization": token, "Content-Type": "application/json"}

    files_payload = {}
    form_files = form_files or {}
    for field_name, remote_key in IALERT_FILE_MAPPING.get(update_value, []):
        uploaded = form_files.get(field_name)
        if uploaded:
            files_payload[remote_key] = (uploaded.name, uploaded.file, uploaded.content_type)

    api_logger.info(
        "OUTGOING iAlert (AIS140) push — ticket=%s update_to_al_api=%s files=%s url=%s payload=%s",
        ticket.unique_id, update_value, list(files_payload.keys()), settings.AIS140_IALERT_PUSH_URL, payload,
    )

    try:
        if files_payload:
            # multipart — payload becomes form fields alongside the files
            response = requests.post(
                settings.AIS140_IALERT_PUSH_URL,
                data=payload,
                files=files_payload,
                headers={"Authorization": headers["Authorization"]},
                timeout=30,
            )
        else:
            response = requests.post(
                settings.AIS140_IALERT_PUSH_URL, json=payload, headers=headers, timeout=30
            )
    except requests.RequestException as exc:
        api_logger.error("OUTGOING iAlert (AIS140) push FAILED — ticket=%s: %s", ticket.unique_id, exc)
        raise IAlertPushError(f"iAlert request failed: {exc}") from exc

    if response.status_code != 200:
        api_logger.error(
            "INCOMING iAlert (AIS140) push REJECTED — ticket=%s status=%s body=%s",
            ticket.unique_id, response.status_code, response.text[:300],
        )
        raise IAlertPushError(f"iAlert rejected the update (HTTP {response.status_code}): "
                               f"{response.text[:300]}")

    api_logger.info(
        "INCOMING iAlert (AIS140) push OK — ticket=%s status=%s body=%s",
        ticket.unique_id, response.status_code, response.text[:500],
    )
    logger.info("iAlert accepted update for ticket %s (%s)", ticket.unique_id, update_value)
    return response.json() if response.content else {}

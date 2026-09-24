# =============================================================================
# crsc_calls — services/ialert.py
# Pushes a follow-up round (remark + comment) to the AL iAlert API for
# iAlert-originated calls only (call_type == "ialert_call"). Direct calls
# never go through this — they save straight through after form validation.
#
# Flow: generate a token from the login endpoint, then POST the update to
# the support-ticket-status endpoint using that token. The local record must
# NOT be saved if either step fails — see views.engineer_form, which raises
# IAlertPushError all the way out to the UI so the engineer sees exactly why
# the submission didn't go through.
# =============================================================================
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)
api_logger = logging.getLogger("api_traffic")


class IAlertPushError(Exception):
    """Raised when the iAlert token request or the support-ticket-status push fails."""


def _get_ialert_token():
    """Requests a fresh token from the iAlert login endpoint. Returns the
    token string, or raises IAlertPushError if the login call fails or
    returns no usable token."""
    if not settings.CRSC_IALERT_LOGIN_URL:
        raise IAlertPushError("CRSC_IALERT_LOGIN_URL is not configured.")

    headers = {"token": settings.CRSC_IALERT_LOGIN_TOKEN_HEADER_VALUE}

    try:
        response = requests.get(settings.CRSC_IALERT_LOGIN_URL, headers=headers, timeout=30)
    except requests.RequestException as exc:
        api_logger.error("iAlert token request FAILED: %s", exc)
        raise IAlertPushError(f"Could not reach the iAlert login endpoint: {exc}") from exc

    if response.status_code != 200:
        api_logger.error(
            "iAlert token request REJECTED — status=%s body=%s",
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
        api_logger.error("iAlert token response had no usable token: %s", response.text[:300])
        raise IAlertPushError("iAlert login succeeded but returned no token.")

    return token


def push_follow_up_to_ialert(call):
    """
    Sends the current follow-up round (remark + comment) for `call` to the
    AL iAlert support-ticket-status API. Only meaningful for
    call_type == "ialert_call" — callers are responsible for checking that.

    Raises IAlertPushError on any failure (network error, non-200 response).
    Returns True on success (HTTP 200).
    """
    if not settings.CRSC_IALERT_PUSH_URL:
        raise IAlertPushError("CRSC_IALERT_PUSH_URL is not configured.")

    token = _get_ialert_token()

    payload = {
        "ticket_id": call.ialert_ticket_no,
        "remarks": call.follow_up_remark,
        "comments": call.follow_up_comment,
        "engineer_name": call.complaint_assigned_to,
    }
    headers = {"Authorization": token, "Content-Type": "application/json"}

    api_logger.info(
        "OUTGOING iAlert push — unique_id=%s ticket=%s payload=%s",
        call.unique_id, call.ialert_ticket_no, payload,
    )

    try:
        response = requests.post(settings.CRSC_IALERT_PUSH_URL, json=payload, headers=headers, timeout=30)
    except requests.RequestException as exc:
        api_logger.error("OUTGOING iAlert push FAILED — unique_id=%s: %s", call.unique_id, exc)
        raise IAlertPushError(f"iAlert request failed: {exc}") from exc

    if response.status_code != 200:
        api_logger.error(
            "OUTGOING iAlert push REJECTED — unique_id=%s status=%s body=%s",
            call.unique_id, response.status_code, response.text[:300],
        )
        raise IAlertPushError(
            f"iAlert rejected the update (HTTP {response.status_code}): {response.text[:300]}"
        )

    api_logger.info("OUTGOING iAlert push OK — unique_id=%s status=%s", call.unique_id, response.status_code)
    return True

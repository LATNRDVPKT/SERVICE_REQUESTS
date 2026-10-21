# =============================================================================
# customer_requests — services/ialert.py
# Pushes a follow-up round (remark + comment) to the AL iAlert API — only for
# calls that originated FROM an AL API push in the first place
# (complaint_received_by == "A.L API"), on every engineer_form submit.
# Manually-created calls (even iAlert-type ones) never go through this, since
# AL has no ticket to update.
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

from customer_requests.services.workflow import build_update_to_al

logger = logging.getLogger(__name__)
api_logger = logging.getLogger("api_traffic")


class IAlertPushError(Exception):
    """Raised when the iAlert token request or the support-ticket-status push fails."""


def _get_ialert_token(context_label=""):
    """Requests a fresh token from the iAlert login endpoint. Returns the
    token string, or raises IAlertPushError if the login call fails or
    returns no usable token. `context_label` (e.g. the call's unique_id) is
    included in every log line so a token failure can still be traced back
    to the call/push attempt that triggered it."""
    prefix = f"unique_id={context_label} " if context_label else ""

    if not settings.CRSC_IALERT_LOGIN_URL:
        raise IAlertPushError("CRSC_IALERT_LOGIN_URL is not configured.")

    headers = {"token": settings.CRSC_IALERT_LOGIN_TOKEN_HEADER_VALUE}

    try:
        response = requests.get(settings.CRSC_IALERT_LOGIN_URL, headers=headers, timeout=30)
    except requests.RequestException as exc:
        api_logger.error("iAlert token request FAILED — %s%s", prefix, exc)
        raise IAlertPushError(f"Could not reach the iAlert login endpoint: {exc}") from exc

    if response.status_code != 200:
        api_logger.error(
            "iAlert token request REJECTED — %sstatus=%s body=%s",
            prefix, response.status_code, response.text[:300],
        )
        raise IAlertPushError(f"iAlert login failed (HTTP {response.status_code}).")

    try:
        body = response.json()
    except ValueError:
        # Login endpoint returned plain text instead of JSON.
        token = response.text.strip()
    else:
        token = body.get("token") or body.get("access_token")
        if not token:
            # Some AL responses nest the token under "data" instead of at
            # the top level — e.g. {"data": {"token": "..."}}. Drill into
            # it rather than handing the whole dict back as the "token".
            nested = body.get("data")
            if isinstance(nested, dict):
                token = nested.get("token") or nested.get("access_token")
            elif isinstance(nested, str):
                token = nested

    if not token or not isinstance(token, str):
        api_logger.error("iAlert token response had no usable token — %s%s", prefix, response.text[:300])
        raise IAlertPushError("iAlert login succeeded but returned no token.")

    # Never log the token itself — it's a live credential.
    api_logger.info("iAlert token request OK — %sstatus=%s", prefix, response.status_code)
    return token


def push_follow_up_to_ialert(call):
    """
    Sends the current follow-up round for `call` to the AL iAlert
    support-ticket-status API. Only meaningful for
    complaint_received_by == "A.L API" — callers are responsible for
    checking that.

    "remarks" is the D1/D2/D3-prefixed string (e.g. "D1 - CUSTOMER NOT
    ANSWERING"), same convention build_update_to_al() already uses — the
    first push is "D1 - ...", the next "D2 - ...", and every push after the
    follow-up reaches D3 stays "D3 - ..." (follow_up_level itself never
    advances past D3 — see services/workflow.py).

    Raises IAlertPushError on any failure (network error, non-200 response).
    Returns True on success (HTTP 200).
    """
    if not settings.CRSC_IALERT_PUSH_URL:
        raise IAlertPushError("CRSC_IALERT_PUSH_URL is not configured.")

    payload = {
        "ticket_id": str(call.ialert_ticket_no or ""),
        "remarks": str(build_update_to_al(call) or ""),
        "comments": str(call.follow_up_comment or ""),
        "engineer_name": str(call.follow_up_engineer or ""),
    }

    # Logged before the token request — so a login failure still leaves a
    # clear record of exactly which call/payload the push was for, instead
    # of just a bare "token rejected" line with no context.
    api_logger.info(
        "OUTGOING iAlert push — unique_id=%s ticket=%s url=%s payload=%s",
        call.unique_id, call.ialert_ticket_no, settings.CRSC_IALERT_PUSH_URL, payload,
    )

    token = _get_ialert_token(context_label=call.unique_id)
    headers = {"Authorization": token, "Content-Type": "application/json"}

    try:
        response = requests.post(settings.CRSC_IALERT_PUSH_URL, json=payload, headers=headers, timeout=30)
    except requests.RequestException as exc:
        api_logger.error("OUTGOING iAlert push FAILED — unique_id=%s: %s", call.unique_id, exc)
        raise IAlertPushError(f"iAlert request failed: {exc}") from exc

    if response.status_code != 200:
        api_logger.error(
            "INCOMING iAlert push REJECTED — unique_id=%s status=%s body=%s",
            call.unique_id, response.status_code, response.text[:300],
        )
        raise IAlertPushError(
            f"iAlert rejected the update (HTTP {response.status_code}): {response.text[:300]}"
        )

    # AL answers HTTP 200 even when it refuses the update; the real verdict
    # is in the JSON body, e.g. {"message": "Failure", "statuscode": 400}.
    try:
        body = response.json()
    except ValueError:
        body = None
    if isinstance(body, dict):
        body_code = str(body.get("statuscode", "")).strip()
        body_message = str(body.get("message", "")).strip().lower()
        if (body_code and body_code != "200") or body_message == "failure":
            api_logger.error(
                "INCOMING iAlert push REJECTED (in body) — unique_id=%s status=%s body=%s",
                call.unique_id, response.status_code, response.text[:300],
            )
            raise IAlertPushError(
                f"iAlert rejected the update: {body.get('data') or body.get('message') or response.text[:300]}"
            )

    api_logger.info(
        "INCOMING iAlert push OK — unique_id=%s status=%s body=%s",
        call.unique_id, response.status_code, response.text[:500],
    )
    return True

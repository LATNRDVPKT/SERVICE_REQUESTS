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
import mimetypes

import requests
from django.conf import settings

from AIS140_FLOW.constants import IALERT_FILE_MAPPING

logger = logging.getLogger(__name__)
api_logger = logging.getLogger("api_traffic")

class IAlertPushError(Exception):
    """Raised when the iAlert token request or the update push fails."""

def _file_blob(source):
    """
    Returns (filename, content_bytes, content_type) for either a freshly
    uploaded file (from request.FILES on this exact submit) or an
    already-stored FieldFile from a previous save — so a certificate
    uploaded on an earlier Part-B save still gets pushed as a blob on every
    later submit, not just the one where it was uploaded.
    """
    if hasattr(source, "content_type"):
        # Freshly uploaded via this request.
        return source.name.split("/")[-1], source.read(), source.content_type

    # Already-stored FieldFile.
    source.open()
    try:
        content = source.read()
    finally:
        source.close()
    content_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
    return source.name.split("/")[-1], content, content_type

def _get_ialert_token(context_label=""):
    """Requests a fresh token from the iAlert login endpoint. Returns the
    token string, or raises IAlertPushError if the login call fails or
    returns no usable token. `context_label` (e.g. the ticket unique_id)
    is included in every log line so a token failure can still be traced
    back to the ticket/push attempt that triggered it."""
    prefix = f"ticket={context_label} " if context_label else ""

    if not settings.AIS140_IALERT_LOGIN_URL:
        raise IAlertPushError("AIS140_IALERT_LOGIN_URL is not configured.")

    headers = {"token": settings.AIS140_IALERT_LOGIN_TOKEN_HEADER_VALUE}

    try:
        response = requests.get(settings.AIS140_IALERT_LOGIN_URL, headers=headers, timeout=30)
    except requests.RequestException as exc:
        api_logger.error("iAlert (AIS140) token request FAILED — %s%s", prefix, exc)
        raise IAlertPushError(f"Could not reach the iAlert login endpoint: {exc}") from exc

    if response.status_code != 200:
        api_logger.error(
            "iAlert (AIS140) token request REJECTED — %sstatus=%s body=%s",
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
        api_logger.error("iAlert (AIS140) token response had no usable token — %s%s", prefix, response.text[:300])
        raise IAlertPushError("iAlert login succeeded but returned no token.")

    # Never log the token itself — it's a live credential.
    api_logger.info("iAlert (AIS140) token request OK — %sstatus=%s", prefix, response.status_code)
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

    files_payload = {}
    form_files = form_files or {}
    for field_name, remote_key in IALERT_FILE_MAPPING.get(update_value, []):
        source = form_files.get(field_name) or getattr(ticket, field_name, None)
        if source:
            files_payload[remote_key] = _file_blob(source)

    # Logged before the token request — so a login failure still leaves a
    # clear record of exactly which ticket/payload the push was for,
    # instead of just a bare "token rejected" line with no context.
    api_logger.info(
        "OUTGOING iAlert (AIS140) push — ticket=%s update_to_al_api=%s files=%s url=%s payload=%s",
        ticket.unique_id, update_value, list(files_payload.keys()), settings.AIS140_IALERT_PUSH_URL, payload,
    )

    token = _get_ialert_token(context_label=ticket.unique_id)
    headers = {"Authorization": token, "Content-Type": "application/json"}

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
                "INCOMING iAlert (AIS140) push REJECTED (in body) — ticket=%s status=%s body=%s",
                ticket.unique_id, response.status_code, response.text[:300],
            )
            raise IAlertPushError(
                f"iAlert rejected the update: {body.get('data') or body.get('message') or response.text[:300]}"
            )

    api_logger.info(
        "INCOMING iAlert (AIS140) push OK — ticket=%s status=%s body=%s",
        ticket.unique_id, response.status_code, response.text[:500],
    )
    logger.info("iAlert accepted update for ticket %s (%s)", ticket.unique_id, update_value)
    return response.json() if response.content else {}

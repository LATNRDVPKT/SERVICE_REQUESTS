# =============================================================================
# AIS140_FLOW — services/ialert.py
# Pushes a Part-B update to iAlert for API-originated tickets
# (request_id present). The local DB is only written by the caller if this
# push succeeds — see views.part_b_form.
# =============================================================================
import logging

import requests
from django.conf import settings

from AIS140_FLOW.constants import IALERT_FILE_MAPPING

logger = logging.getLogger(__name__)


class IAlertPushError(Exception):
    """Raised when iAlert rejects or fails to accept an update."""


def push_update_to_ialert(ticket, form_files=None):
    """
    Build and send the outbound payload to iAlert for this ticket, based on
    ticket.Update_to_AL_API. Raises IAlertPushError on any non-2xx response
    or network failure — callers must not save the ticket locally if this
    raises.
    """
    if not settings.IALERT_BASE_URL:
        raise IAlertPushError("IALERT_BASE_URL is not configured.")

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

    headers = {
        "Authorization": f"Bearer {settings.IALERT_TOKEN_HEADER_VALUE}",
        "Content-Type": "application/json",
    }

    files_payload = {}
    form_files = form_files or {}
    for field_name, remote_key in IALERT_FILE_MAPPING.get(update_value, []):
        uploaded = form_files.get(field_name)
        if uploaded:
            files_payload[remote_key] = (uploaded.name, uploaded.file, uploaded.content_type)

    try:
        if files_payload:
            # multipart — payload becomes form fields alongside the files
            response = requests.post(
                settings.IALERT_BASE_URL,
                data=payload,
                files=files_payload,
                headers={"Authorization": headers["Authorization"]},
                timeout=30,
            )
        else:
            response = requests.post(
                settings.IALERT_BASE_URL, json=payload, headers=headers, timeout=30
            )
    except requests.RequestException as exc:
        raise IAlertPushError(f"iAlert request failed: {exc}") from exc

    if response.status_code != 200:
        raise IAlertPushError(f"iAlert rejected the update (HTTP {response.status_code}): "
                               f"{response.text[:300]}")

    logger.info("iAlert accepted update for ticket %s (%s)", ticket.unique_id, update_value)
    return response.json() if response.content else {}

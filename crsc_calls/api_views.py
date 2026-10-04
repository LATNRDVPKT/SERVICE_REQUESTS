# =============================================================================
# crsc_calls — api_views.py
# DRF-based ticket intake API for AL/iAlert.
#
# POST /crsc/api/create-ticket/
#   - No `danlaw_unique_id` in the payload -> creates a new CRSC call.
#     vinNumber, callbackNo and ticketId are mandatory (see serializers.py).
#   - `danlaw_unique_id` present -> updates the matching call's iAlert
#     remarks/comments. Two recognised remark values trigger extra business
#     logic (contact update / reassignment) plus an e-mail to whoever's
#     assigned — everything else just refreshes iAlert Remarks.
# =============================================================================
import logging

import pytz
from django.urls import reverse
from django.utils.timezone import now
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from core.api_auth import ALTokenAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DirectCall
from .serializers import CRSCTicketCreateSerializer, CRSCTicketUpdateSerializer
from .services.email_utils import send_ialert_update_email
from .services.workflow import apply_follow_up_rules, write_history_rows

logger = logging.getLogger(__name__)
api_logger = logging.getLogger("api_traffic")

IST = pytz.timezone("Asia/Kolkata")

CONTACT_UPDATE_REMARK = "Assigned to Danlaw – Contact Update"
REASSIGNED_REMARK = "Assigned to Danlaw - new"


def _sanitize_nulls(data):
    """AL sends explicit JSON null for unset optional fields (not just
    omitted keys) — DRF CharField rejects None unless allow_null=True is set
    on every such field individually, so instead we normalize None -> ""
    once here before validation, matching what an omitted key would already
    default to."""
    return {k: ("" if v is None else v) for k, v in data.items()}


class CRSCTicketIntakeAPIView(APIView):
    """Single dispatching endpoint — create when no identifier is given,
    update when one is. This is a server-to-server webhook (AL calling in),
    not a user-facing endpoint, hence no authentication."""

    authentication_classes = [ALTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = _sanitize_nulls(request.data)
        api_logger.info("INCOMING crsc api_create_ticket — payload=%s", data)

        danlaw_unique_id = (data.get("danlaw_unique_id") or "").strip()
        if not danlaw_unique_id:
            return self._create(data)
        return self._update(request, danlaw_unique_id, data)

    def _create(self, data):
        serializer = CRSCTicketCreateSerializer(data=data)
        if not serializer.is_valid():
            api_logger.error("INCOMING crsc api_create_ticket — validation failed: %s", serializer.errors)
            return Response(
                {"success": False, "action": "Not-Created — invalid payload", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        v = serializer.validated_data

        alt_contacts = ";".join(c for c in [v["driverContact"], v["serviceContact"]] if c)

        call = DirectCall.objects.create(
            date_of_complaint=now().astimezone(IST),
            complaint_raised_from_location=v["areaName"],
            customer_raised_issue=v["issueDescription"],
            complaint_raised=v["designation"],
            complaint_raised_by=v["customerName"],
            contact_number=v["callbackNo"],
            customer_mail_id=v["customerMailId"],
            complaint_raised_through="I-Alert PD API",
            call_type="ialert_call",
            vin=v["vinNumber"],
            psn=v["deviceId"],
            ialert_ticket_no=v["ticketId"],
            vehicle_avl_in_workshop="No",
            complaint_received_by="A.L API",
            complaint_assigned_to="--",
            updated_contact_no=alt_contacts,
            ialert_remarks=v["remarks"],
            # Danlaw owns every ticket from the moment it's created until an
            # engineer/manager update says otherwise.
            responsibility="DANLAW",
        )

        api_logger.info(
            "INCOMING crsc api_create_ticket OK — unique_id=%s ticket_id=%s",
            call.unique_id, call.id,
        )
        return Response(
            {"success": True, "action": "created", "ticket_id": call.id, "unique_id": call.unique_id},
            status=status.HTTP_201_CREATED,
        )

    def _update(self, request, danlaw_unique_id, data):
        serializer = CRSCTicketUpdateSerializer(data={**data, "danlaw_unique_id": danlaw_unique_id})
        if not serializer.is_valid():
            api_logger.error("INCOMING crsc api_update_ticket — validation failed: %s", serializer.errors)
            return Response(
                {"success": False, "action": "Not-Updated — invalid payload", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        v = serializer.validated_data
        remarks = v["remarks"].strip()
        comments = v["comments"].strip()

        try:
            call = DirectCall.objects.get(unique_id=danlaw_unique_id)
        except DirectCall.DoesNotExist:
            api_logger.error("INCOMING crsc api_update_ticket — unknown unique_id=%s", danlaw_unique_id)
            return Response(
                {"success": False, "action": "No ticket found for given danlaw_unique_id",
                 "ticket_id": None, "unique_id": danlaw_unique_id},
                status=status.HTTP_404_NOT_FOUND,
            )

        previous = DirectCall.objects.get(pk=call.pk)
        email_triggered = False

        if remarks == CONTACT_UPDATE_REMARK:
            call.al_updated_contact_no = comments
            call.ialert_remarks = remarks
            email_triggered = True
        elif remarks == REASSIGNED_REMARK:
            call.call_status = "Pending"
            call.ialert_remarks = remarks
            email_triggered = True
        elif remarks:
            call.ialert_remarks = remarks

        # Reuses the same follow-up/history engine as the engineer form —
        # an al_updated_contact_no change here is picked up and logged the
        # exact same way a manual Part-B save would.
        history_rows = apply_follow_up_rules(call, previous)
        call.save()
        write_history_rows(call, history_rows)

        api_logger.info(
            "INCOMING crsc api_update_ticket OK — unique_id=%s remarks=%r", danlaw_unique_id, remarks,
        )

        if email_triggered:
            part_b_url = request.build_absolute_uri(reverse("crsc_engineer_form", args=[call.id]))
            send_ialert_update_email(call, remarks, comments, part_b_url)

        return Response({"success": True, "action": "updated", "ticket_id": call.id, "unique_id": call.unique_id})

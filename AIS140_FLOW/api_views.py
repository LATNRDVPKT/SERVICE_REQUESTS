# =============================================================================
# AIS140_FLOW — api_views.py
# DRF-based AL ticket intake API — two server-to-server webhooks, no
# authentication (AL calling in, not a user-facing endpoint):
#
# POST /ais140/api/create-ais140-ticket/   — creates a new AIS140Request.
# POST /ais140/api/update-ais140-remarks/  — pushes AL_remarks/AL_comments
#   onto an existing ticket (matched by request_id), reopens it to Pending,
#   and stamps reupdated_request_al — every AL remarks push counts as AL
#   having re-engaged with this request.
# =============================================================================
import logging

from django.utils.timezone import now
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from core.api_auth import ALTokenAuthentication

from .constants import TEMP_CERT_DEFAULT_YES_STATES
from .models import AIS140Request
from .serializers import AIS140TicketCreateSerializer, AIS140RemarksUpdateSerializer
from .services.darby import run_darby_lookup_and_save
from .services.email_utils import send_remarks_updated_email
from .services.workflow import write_history_rows

logger = logging.getLogger(__name__)
api_logger = logging.getLogger("api_traffic")


def _sanitize_nulls(data):
    """AL sends explicit JSON null for unset optional fields (not just
    omitted keys) — e.g. "sos_confirmed_on": null. DRF CharField rejects
    None unless allow_null=True is set on every such field individually, so
    instead we normalize None -> "" once here before validation, matching
    what an omitted key would already default to."""
    return {k: ("" if v is None else v) for k, v in data.items()}


class AIS140TicketCreateAPIView(APIView):
    authentication_classes = [ALTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = _sanitize_nulls(request.data)
        api_logger.info(
            "INCOMING api_create_ais140_ticket — from=%s payload=%s",
            request.META.get("REMOTE_ADDR"), data,
        )

        serializer = AIS140TicketCreateSerializer(data=data)
        if not serializer.is_valid():
            api_logger.error("INCOMING api_create_ais140_ticket — validation failed: %s", serializer.errors)
            return Response(
                {"error": "Missing required fields.", "fields": list(serializer.errors.keys())},
                status=status.HTTP_400_BAD_REQUEST,
            )
        v = serializer.validated_data

        created_at = now()
        ticket = AIS140Request.objects.create(
            request_id=v["request_id"],
            date_of_request=created_at,
            Customer_assigned_date=created_at,
            D1_TAT="00:00:00",
            state=v["state"],
            vin_no=v["chassis_number"],
            engine=v["engine_no"],
            psn=v["obu_id"],
            vehicle_no=v["vehicle_reg_no"],
            vehicle_model=v["vehicle_model"],
            customer_name=v["customer_name"],
            customer_phone=v["customer_mobile_number"],
            Customer_mobile_number=v["customer_mobile_number"],
            Customer_Alternate_number=v["customer_alternate_number"],
            Customer_Email_ID=v["customer_email_id"],
            Cust_veh_Regn_Address=v["cust_veh_regn_address"],
            Cust_veh_Regn_Pincode=v["cust_veh_regn_pincode"],
            pan_card=v["pan_no"],
            aadhar_card=v["aadhar_no"],
            manufacturing_year=v["mfg_year"],
            request_type=v["ais140_type"],
            AIS140_Type=v["ais140_type"].strip().title(),
            rto_name=v["rto_name"],
            rto_code=v["rto_code"],
            dealer_name=v["dealer_name"],
            dealer_code=v["dealer_code"],
            Dealer_Contact=v["dealer_contact"],
            Dealer_Location=v["dealer_location"],
            Dealer_mail=v["dealer_email_id"],
            TSM_mail=v["tsm_email_id"],
            Ialert_Email_ID=v["ialert_email_id"],
            sos_fitment_date=v["sos_confirmed_on"] or None,
            zone=v["zoneName"],
            category=v["category"],
            ticket_through="A.L API",
            assigned_engineer_email="--",
            temp_cert_reqd="Yes" if v["state"].strip().upper() in TEMP_CERT_DEFAULT_YES_STATES else "No",
            # Danlaw owns every ticket from the moment it's created until an
            # engineer/manager update says otherwise.
            responsibility="DANLAW",
        )

        # REQ-13 — Darby auto-lookup right after ticket creation
        run_darby_lookup_and_save(ticket)

        api_logger.info(
            "INCOMING api_create_ais140_ticket OK — request_id=%s unique_id=%s",
            ticket.request_id, ticket.unique_id,
        )
        return Response({"unique_id": ticket.unique_id, "id": ticket.id}, status=status.HTTP_201_CREATED)


class AIS140RemarksUpdateAPIView(APIView):
    authentication_classes = [ALTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = _sanitize_nulls(request.data)
        api_logger.info("Payload Re-Update from A.L: %s", data)

        serializer = AIS140RemarksUpdateSerializer(data=data)
        if not serializer.is_valid():
            api_logger.error("INCOMING api_update_ais140_remarks — validation failed: %s", serializer.errors)
            return Response(
                {"error": "request_id is required.", "fields": list(serializer.errors.keys())},
                status=status.HTTP_400_BAD_REQUEST,
            )
        v = serializer.validated_data
        request_id = v["request_id"]
        vin_no = v["vin_no"].strip()
        remarks = v["remarks"].strip()
        comments = v["comments"].strip()

        try:
            ticket = AIS140Request.objects.get(request_id=request_id)
        except AIS140Request.DoesNotExist:
            api_logger.error("INCOMING api_update_ais140_remarks — unknown request_id=%s", request_id)
            return Response(
                {"error": "No ticket found for that request_id."}, status=status.HTTP_404_NOT_FOUND,
            )

        # request_id is the authoritative match key — vin_no is only
        # cross-checked for an audit trail, never used to block the update.
        if vin_no and ticket.vin_no and vin_no.upper() != ticket.vin_no.strip().upper():
            api_logger.warning(
                "INCOMING api_update_ais140_remarks — vin_no mismatch request_id=%s payload_vin=%s ticket_vin=%s",
                request_id, vin_no, ticket.vin_no,
            )

        timestamp = now()
        ticket.AL_remarks = remarks
        ticket.AL_comments = comments
        ticket.al_remarks_updated_at = timestamp
        ticket.reupdated_request_al = timestamp
        ticket.reupdated_request_al_updated_at = timestamp
        ticket.completion_status = "Pending"
        ticket.save(update_fields=[
            "AL_remarks", "AL_comments", "al_remarks_updated_at",
            "reupdated_request_al", "reupdated_request_al_updated_at", "completion_status",
        ])

        write_history_rows(ticket, [
            {"source_field": "al_remarks", "latest_remark": ticket.AL_remarks,
             "latest_comments": ticket.AL_comments, "remark_datetime": timestamp,
             "attending_engineer": ticket.attending_engineer},
            {"source_field": "reupdated_request_al", "latest_remark": str(ticket.reupdated_request_al),
             "latest_comments": "", "remark_datetime": timestamp,
             "attending_engineer": ticket.attending_engineer},
        ])

        send_remarks_updated_email(ticket)
        api_logger.info(
            "INCOMING api_update_ais140_remarks OK — request_id=%s unique_id=%s", request_id, ticket.unique_id,
        )
        return Response({"status": "ok", "unique_id": ticket.unique_id})

# =============================================================================
# crsc_calls — serializers.py
# DRF serializers for the AL/iAlert ticket intake API (api_views.py).
# =============================================================================
from rest_framework import serializers

from .models import CONTACT_NUMBER_VALIDATOR, VIN_VALIDATOR


class CRSCTicketCreateSerializer(serializers.Serializer):
    """
    Validates the payload for creating a new CRSC call from an AL/iAlert
    ticket. VIN, contact number (callbackNo) and the AL ticket ID are
    mandatory — everything else is optional context.
    """
    vinNumber = serializers.CharField(validators=[VIN_VALIDATOR])
    callbackNo = serializers.CharField(validators=[CONTACT_NUMBER_VALIDATOR])
    ticketId = serializers.CharField(max_length=50)

    areaName = serializers.CharField(required=False, allow_blank=True, default="")
    issueDescription = serializers.CharField(required=False, allow_blank=True, default="")
    designation = serializers.CharField(required=False, allow_blank=True, default="")
    customerName = serializers.CharField(required=False, allow_blank=True, default="")
    driverContact = serializers.CharField(required=False, allow_blank=True, default="")
    serviceContact = serializers.CharField(required=False, allow_blank=True, default="")
    customerMailId = serializers.CharField(required=False, allow_blank=True, default="")
    deviceId = serializers.CharField(required=False, allow_blank=True, default="")
    comments = serializers.CharField(required=False, allow_blank=True, default="")
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class CRSCTicketUpdateSerializer(serializers.Serializer):
    """
    Validates the payload for updating an existing CRSC call. Only
    danlaw_unique_id is mandatory here — this endpoint is used for
    lightweight remark/contact-update pushes from AL, not full re-intake.
    """
    danlaw_unique_id = serializers.CharField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
    comments = serializers.CharField(required=False, allow_blank=True, default="")

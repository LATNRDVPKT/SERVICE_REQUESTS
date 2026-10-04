# =============================================================================
# AIS140_FLOW — serializers.py
# DRF serializers for the AL ticket create/remarks-update intake API
# (api_views.py).
# =============================================================================
from rest_framework import serializers


class AIS140TicketCreateSerializer(serializers.Serializer):
    """Mandatory fields match the AL ticket-creation contract exactly —
    same set previously enforced by REQUIRED_API_FIELDS."""
    request_id = serializers.CharField()
    request_date = serializers.CharField()
    state = serializers.CharField()
    chassis_number = serializers.CharField()
    engine_no = serializers.CharField()
    obu_id = serializers.CharField()
    # Blank for a brand-new vehicle that hasn't been RTO-registered yet
    # (real AL payloads send "" here for ais140_type="new" requests).
    vehicle_reg_no = serializers.CharField(required=False, allow_blank=True, default="")
    vehicle_model = serializers.CharField()
    customer_name = serializers.CharField()
    customer_mobile_number = serializers.CharField()
    pan_no = serializers.CharField()
    aadhar_no = serializers.CharField()
    mfg_year = serializers.CharField()
    rto_name = serializers.CharField()
    rto_code = serializers.CharField()
    dealer_name = serializers.CharField()
    dealer_code = serializers.CharField()

    customer_alternate_number = serializers.CharField(required=False, allow_blank=True, default="")
    customer_email_id = serializers.CharField(required=False, allow_blank=True, default="")
    cust_veh_regn_address = serializers.CharField(required=False, allow_blank=True, default="")
    cust_veh_regn_pincode = serializers.CharField(required=False, allow_blank=True, default="")
    ais140_type = serializers.CharField(required=False, allow_blank=True, default="")
    dealer_contact = serializers.CharField(required=False, allow_blank=True, default="")
    dealer_location = serializers.CharField(required=False, allow_blank=True, default="")
    dealer_email_id = serializers.CharField(required=False, allow_blank=True, default="")
    tsm_email_id = serializers.CharField(required=False, allow_blank=True, default="")
    ialert_email_id = serializers.CharField(required=False, allow_blank=True, default="")
    sos_confirmed_on = serializers.CharField(required=False, allow_blank=True, default="")
    zoneName = serializers.CharField(required=False, allow_blank=True, default="")
    category = serializers.CharField(required=False, allow_blank=True, default="")


class AIS140RemarksUpdateSerializer(serializers.Serializer):
    """request_id is the authoritative match key — vin_no is only used for
    a cross-check audit log, never to block the update."""
    request_id = serializers.CharField()
    vin_no = serializers.CharField(required=False, allow_blank=True, default="")
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
    comments = serializers.CharField(required=False, allow_blank=True, default="")

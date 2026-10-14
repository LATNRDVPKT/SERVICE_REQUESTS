# =============================================================================
# crsc_calls — services/feedback.py
# Signed, expiring links for the public customer-feedback page. The token is
# just the signed call id — no DB column needed, and a customer can't guess
# another call's link.
# =============================================================================
from django.core import signing

FEEDBACK_SALT = "crsc-customer-feedback"
FEEDBACK_LINK_MAX_AGE = 60 * 60 * 24 * 90  # 90 days


def make_feedback_token(call_id):
    return signing.dumps({"call": call_id}, salt=FEEDBACK_SALT)


def read_feedback_token(token):
    """Returns the call id, or None if the token is tampered with / expired."""
    try:
        data = signing.loads(token, salt=FEEDBACK_SALT, max_age=FEEDBACK_LINK_MAX_AGE)
    except signing.BadSignature:  # also covers SignatureExpired
        return None
    return data.get("call")

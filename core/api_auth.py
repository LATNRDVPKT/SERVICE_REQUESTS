# =============================================================================
# core — api_auth.py
# Bearer-token authentication for the endpoints the AL team calls.
#
# Every request must send:   Authorization: Bearer <AL_API_TOKEN>
# Missing, malformed, or wrong tokens get 401. If AL_API_TOKEN is not
# configured at all, every request is rejected (fails closed).
# =============================================================================
import hmac

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class ALTeamClient:
    """Stand-in principal for an authenticated AL team caller."""
    is_authenticated = True
    is_anonymous = False
    username = "al-team"

    def __str__(self):
        return self.username


class ALTokenAuthentication(BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header:
            raise AuthenticationFailed("Missing Authorization header.")

        parts = header.split()
        if len(parts) != 2 or parts[0].lower() != self.keyword.lower():
            raise AuthenticationFailed("Authorization header must be 'Bearer <token>'.")

        expected = settings.AL_API_TOKEN
        if not expected:
            raise AuthenticationFailed("AL API token is not configured on this server.")

        if not hmac.compare_digest(parts[1].encode(), expected.encode()):
            raise AuthenticationFailed("Invalid API token.")

        return (ALTeamClient(), parts[1])

    def authenticate_header(self, request):
        return self.keyword

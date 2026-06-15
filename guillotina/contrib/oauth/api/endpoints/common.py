from guillotina.api.service import Service
from guillotina.contrib.oauth.storage.access import get_oauth_store
from guillotina.response import Response


# Parameters that must appear at most once per request. Repeated occurrences are
# rejected to avoid OAuth parameter-pollution attacks.
AUTHORIZATION_REQUEST_SINGLETON_PARAMS = {
    "response_type",
    "client_id",
    "redirect_uri",
    "scope",
    "state",
    "code_challenge",
    "code_challenge_method",
    "decision",
    "username",
    "password",
    "oauth_csrf",
}
TOKEN_REQUEST_SINGLETON_PARAMS = {
    "grant_type",
    "client_id",
    "redirect_uri",
    "code",
    "code_verifier",
    "refresh_token",
    "scope",
}
REVOCATION_REQUEST_SINGLETON_PARAMS = {"client_id", "token", "token_type_hint"}
CONSENT_REQUEST_SINGLETON_PARAMS = {"consent_key", "client_id"}


class OAuthService(Service):
    def oauth_store(self):
        return get_oauth_store(self.context)


def token_response(content):
    return Response(
        content=content,
        headers={
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
        },
    )

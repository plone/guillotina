from guillotina import app_settings
from guillotina.api.service import Service
from guillotina.auth.utils import set_authenticated_user
from guillotina.contrib.oauth.flow.csrf import OAUTH_CSRF_FIELD
from guillotina.contrib.oauth.storage.access import get_oauth_store
from guillotina.response import Response


# Parameters that must appear at most once per request. Repeated occurrences are
# rejected to avoid OAuth parameter-pollution attacks.
AUTHORIZE_SINGLETON_PARAMS = {
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
    OAUTH_CSRF_FIELD,
}
TOKEN_SINGLETON_PARAMS = {
    "grant_type",
    "client_id",
    "redirect_uri",
    "code",
    "code_verifier",
    "refresh_token",
    "scope",
}
REVOKE_SINGLETON_PARAMS = {"client_id", "token", "token_type_hint"}
CONSENT_SINGLETON_PARAMS = {"consent_key", "client_id"}


class OAuthService(Service):
    def oauth_store(self):
        return get_oauth_store(self.context)


async def authenticate_basic(username, password):
    creds = {"type": "basic", "token": password, "id": username}
    for validator in app_settings["auth_token_validators"]:
        if validator.for_validators is not None and "basic" not in validator.for_validators:
            continue
        user = await validator().validate(creds)
        if user is not None:
            set_authenticated_user(user)
            return user


def token_response(content):
    return Response(
        content=content,
        headers={
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
        },
    )

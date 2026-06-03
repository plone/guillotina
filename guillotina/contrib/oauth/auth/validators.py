import jwt

from guillotina import app_settings, task_vars
from guillotina.auth import find_user
from guillotina.contrib.oauth.api.urls import container_url
from guillotina.contrib.oauth.flow.resources import oauth_required_audience
from guillotina.contrib.oauth.flow.scopes import OAUTH_DEFAULT_SCOPE
from guillotina.contrib.oauth.flow.tokens import access_token_key


class OAuthJWTValidator:
    for_validators = ("bearer",)

    async def validate(self, token):
        if token.get("type") not in self.for_validators:
            return
        raw = token.get("token", "")
        if "." not in raw:
            return
        try:
            claims = jwt.decode(
                raw,
                access_token_key(),
                algorithms=[app_settings["jwt"]["algorithm"]],
                options={"verify_aud": False},
            )
        except (jwt.exceptions.PyJWTError, KeyError):
            return
        if claims.get("token_type") != "oauth_access_token":
            return
        request = task_vars.request.get(None)
        container = task_vars.container.get(None)
        if request is not None and container is not None:
            issuer = container_url(request, container)
            if claims.get("iss") != issuer:
                return
            aud = set(claims.get("aud") or [])
            if oauth_required_audience(request, container) not in aud:
                return
        if not claims.get("client_id"):
            return
        scopes = set((claims.get("scope") or "").split())
        if OAUTH_DEFAULT_SCOPE not in scopes:
            return
        token["id"] = claims.get("id", claims.get("sub"))
        token["decoded"] = claims
        user = await find_user(token)
        if user is not None and user.id == token["id"]:
            if request is not None:
                request.oauth = {
                    "client_id": claims.get("client_id"),
                    "scopes": scopes,
                    "resources": set(claims.get("aud") or []),
                    "claims": claims,
                }
            return user

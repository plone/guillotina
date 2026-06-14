from guillotina import app_settings
from guillotina.contrib.oauth.api.endpoints.common import REVOKE_SINGLETON_PARAMS
from guillotina.contrib.oauth.api.request import (
    client_identifier,
    form_content_type_valid,
    parse_form_encoded,
)
from guillotina.contrib.oauth.flow.clients import consent_key
from guillotina.contrib.oauth.flow.ratelimit import rate_limit_exceeded
from guillotina.response import HTTPBadRequest, HTTPTooManyRequests


async def revoke(service, store):
    if not form_content_type_valid(service.request):
        return HTTPBadRequest(
            content={"error": "invalid_request", "error_description": "invalid content type"}
        )
    try:
        data = parse_form_encoded(await service.request.text(), singleton_fields=REVOKE_SINGLETON_PARAMS)
    except HTTPBadRequest as exc:
        return exc
    if not data.get("client_id") or not data.get("token"):
        return HTTPBadRequest(content={"error": "invalid_request"})
    if data.get("token_type_hint") == "access_token":
        return HTTPBadRequest(content={"error": "unsupported_token_type"})
    oauth_settings = app_settings.get("oauth", {})
    if await rate_limit_exceeded(
        f"oauth-revoke:{client_identifier(service.request)}",
        limit=oauth_settings.get("revoke_rate_limit", 120),
        window=oauth_settings.get("revoke_rate_window", 60),
    ):
        return HTTPTooManyRequests(
            content={
                "error": "temporarily_unavailable",
                "error_description": "revocation rate limit exceeded",
            }
        )
    record = await store.get_refresh_token(data.get("token", ""))
    if record is not None and record.get("client_id") == data.get("client_id"):
        await store.revoke_refresh_family(
            client_id=record["client_id"],
            user_id=record["user_id"],
            auth_code_hash=record.get("auth_code_hash"),
        )
        # Drop the remembered consent so the grant cannot be silently re-issued
        # after the user revoked their tokens (RFC 9700 deauthorization hygiene).
        await store.delete_consent(
            consent_key(
                record["user_id"],
                record["client_id"],
                record.get("scope") or [],
                record.get("resource") or [],
            ),
            user_id=record["user_id"],
        )
    return {}

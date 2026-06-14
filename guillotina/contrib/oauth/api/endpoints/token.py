from guillotina import app_settings
from guillotina.contrib.oauth.api.endpoints.common import TOKEN_SINGLETON_PARAMS, token_response
from guillotina.contrib.oauth.api.request import (
    client_identifier,
    form_content_type_valid,
    normalize_list,
    parse_form_encoded,
)
from guillotina.contrib.oauth.api.urls import container_url
from guillotina.contrib.oauth.flow.pkce import verify_s256
from guillotina.contrib.oauth.flow.ratelimit import rate_limit_exceeded
from guillotina.contrib.oauth.flow.tokens import issue_access_token, opaque_token, token_hash
from guillotina.response import HTTPBadRequest, HTTPTooManyRequests


async def token(service, store):
    if not form_content_type_valid(service.request):
        return HTTPBadRequest(
            content={"error": "invalid_request", "error_description": "invalid content type"}
        )
    try:
        data = parse_form_encoded(await service.request.text(), singleton_fields=TOKEN_SINGLETON_PARAMS)
    except HTTPBadRequest as exc:
        return exc
    grant_type = data.get("grant_type")
    if not grant_type:
        return HTTPBadRequest(content={"error": "invalid_request"})
    oauth_settings = app_settings.get("oauth", {})
    if await rate_limit_exceeded(
        f"oauth-token:{client_identifier(service.request)}",
        limit=oauth_settings.get("token_rate_limit", 120),
        window=oauth_settings.get("token_rate_window", 60),
    ):
        return HTTPTooManyRequests(
            content={"error": "temporarily_unavailable", "error_description": "token rate limit exceeded"}
        )
    if grant_type == "authorization_code":
        return await _authorization_code(service, store, data)
    if grant_type == "refresh_token":
        return await _refresh_token(service, store, data)
    return HTTPBadRequest(content={"error": "unsupported_grant_type"})


async def _authorization_code(service, store, data):
    if not data.get("client_id") or not data.get("code") or not data.get("redirect_uri"):
        return HTTPBadRequest(content={"error": "invalid_request"})
    client = await store.get_client(data.get("client_id"))
    code_raw = data.get("code", "")
    code_hash_val = token_hash(code_raw)
    record = await store.get_active_code(code_raw)
    if record is None:
        await store.revoke_refresh_tokens_by_auth_code(code_hash_val)
        return HTTPBadRequest(content={"error": "invalid_grant"})
    if client is None or record["client_id"] != client["client_id"]:
        return HTTPBadRequest(content={"error": "invalid_grant"})
    if "authorization_code" not in set(client.get("grant_types") or []):
        return HTTPBadRequest(content={"error": "unauthorized_client"})
    if record["redirect_uri"] != data.get("redirect_uri"):
        return HTTPBadRequest(content={"error": "invalid_grant"})
    if record.get("code_challenge"):
        if not verify_s256(data.get("code_verifier", ""), record["code_challenge"]):
            return HTTPBadRequest(content={"error": "invalid_grant"})
    else:
        # PKCE is mandatory for public clients. A code without a bound challenge is invalid.
        return HTTPBadRequest(content={"error": "invalid_grant"})
    requested_resources = normalize_list(data.get("resource"))
    if requested_resources and not set(requested_resources).issubset(set(record["resource"])):
        return HTTPBadRequest(content={"error": "invalid_target"})
    resources = requested_resources or record["resource"]

    consumed = await store.consume_code(code_raw)
    if consumed is None:
        return HTTPBadRequest(content={"error": "invalid_grant"})
    record = consumed

    access_token, _claims = issue_access_token(
        issuer=container_url(service.request, service.context),
        subject=record["user_id"],
        audience=resources,
        client_id=client["client_id"],
        scope=record["scope"],
    )
    refresh_token = opaque_token("gor_")
    await store.create_refresh_token(
        raw_token=refresh_token,
        client_id=client["client_id"],
        user_id=record["user_id"],
        scope=record["scope"],
        resource=resources,
        auth_code_hash=record["code_hash"],
    )
    return token_response(
        {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": app_settings["oauth"].get("access_token_ttl", 3600),
            "refresh_token": refresh_token,
            "scope": " ".join(record["scope"]),
        }
    )


async def _refresh_token(service, store, data):
    if not data.get("client_id") or not data.get("refresh_token"):
        return HTTPBadRequest(content={"error": "invalid_request"})
    refresh_raw = data.get("refresh_token", "")
    client = await store.get_client(data.get("client_id"))
    record = await store.get_valid_refresh(refresh_raw)
    if record is None:
        cand = await store.get_refresh_token(refresh_raw)
        if cand is not None and cand.get("revoked_at"):
            await store.revoke_refresh_family_for_reuse(
                client_id=cand["client_id"],
                user_id=cand["user_id"],
                auth_code_hash=cand.get("auth_code_hash"),
            )
        return HTTPBadRequest(content={"error": "invalid_grant"})
    if client is None or record["client_id"] != client["client_id"]:
        return HTTPBadRequest(content={"error": "invalid_grant"})
    if "refresh_token" not in set(client.get("grant_types") or []):
        return HTTPBadRequest(content={"error": "unauthorized_client"})
    scopes = normalize_list(data.get("scope")) or record["scope"]
    resources = normalize_list(data.get("resource")) or record["resource"]
    if not set(scopes).issubset(set(record["scope"])) or not set(resources).issubset(set(record["resource"])):
        return HTTPBadRequest(content={"error": "invalid_scope"})
    new_refresh = opaque_token("gor_")
    rotated = await store.rotate_refresh_token(
        old_refresh_raw=refresh_raw,
        new_refresh_raw=new_refresh,
        client_id=client["client_id"],
        scope=scopes,
        resource=resources,
    )
    if not rotated:
        return HTTPBadRequest(content={"error": "invalid_grant"})
    access_token, _claims = issue_access_token(
        issuer=container_url(service.request, service.context),
        subject=record["user_id"],
        audience=resources,
        client_id=client["client_id"],
        scope=scopes,
    )
    return token_response(
        {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": app_settings["oauth"].get("access_token_ttl", 3600),
            "refresh_token": new_refresh,
            "scope": " ".join(scopes),
        }
    )

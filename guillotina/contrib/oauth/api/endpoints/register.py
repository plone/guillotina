from guillotina import app_settings
from guillotina.contrib.oauth.flow.clients import build_client_from_registration
from guillotina.contrib.oauth.utils.ratelimit import rate_limit_exceeded
from guillotina.contrib.oauth.utils.request import peer_ip_address
from guillotina.response import HTTPBadRequest, HTTPTooManyRequests, Response


async def client_registration_endpoint(service, store):
    oauth_settings = app_settings.get("oauth", {})
    if await rate_limit_exceeded(
        f"oauth-register:{peer_ip_address(service.request)}",
        limit=oauth_settings.get("registration_rate_limit", 20),
        window=oauth_settings.get("registration_rate_window", 600),
    ):
        return HTTPTooManyRequests(
            content={
                "error": "temporarily_unavailable",
                "error_description": "client registration rate limit exceeded",
            }
        )
    content_type = service.request.headers.get("content-type", "")
    if content_type.split(";", 1)[0].strip().lower() != "application/json":
        return HTTPBadRequest(
            content={"error": "invalid_request", "error_description": "invalid content type"}
        )
    data = await service.request.json()
    try:
        client = build_client_from_registration(data)
    except HTTPBadRequest as exc:
        return exc
    await store.create_client(client)
    content = {
        key: client[key]
        for key in (
            "client_id",
            "client_name",
            "redirect_uris",
            "grant_types",
            "response_types",
            "scope",
            "token_endpoint_auth_method",
        )
    }
    content["client_id_issued_at"] = client["client_id_issued_at"]
    return Response(
        content=content,
        status=201,
        headers={
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
        },
    )

from guillotina.auth.users import AnonymousUser
from guillotina.contrib.oauth.api.endpoints.common import CONSENT_REQUEST_SINGLETON_PARAMS
from guillotina.contrib.oauth.utils.request import form_content_type_valid, parse_form_encoded
from guillotina.response import HTTPBadRequest, HTTPNotFound, HTTPUnauthorized, Response
from guillotina.utils import get_authenticated_user


async def list_consents_endpoint(service, store):
    user = get_authenticated_user()
    if isinstance(user, AnonymousUser):
        return HTTPUnauthorized(content={"error": "invalid_token"})

    consents = await store.list_consents(user.id)
    clients = {}
    items = []
    for consent in consents:
        client_id = consent["client_id"]
        if client_id not in clients:
            clients[client_id] = await store.get_client(client_id)
        client = clients[client_id] or {}
        items.append(
            {
                "consent_key": consent["consent_key"],
                "client_id": client_id,
                "client_name": client.get("client_name"),
                "scope": consent["scope"],
                "resource": consent["resource"],
                "granted_at": consent["granted_at"],
                "expires_at": consent["expires_at"],
            }
        )
    return Response(content={"consents": items}, headers={"Cache-Control": "no-store"})


async def revoke_consent_endpoint(service, store):
    user = get_authenticated_user()
    if isinstance(user, AnonymousUser):
        return HTTPUnauthorized(content={"error": "invalid_token"})

    if not form_content_type_valid(service.request):
        return HTTPBadRequest(
            content={"error": "invalid_request", "error_description": "invalid content type"}
        )
    try:
        data = parse_form_encoded(
            await service.request.text(), singleton_fields=CONSENT_REQUEST_SINGLETON_PARAMS
        )
    except HTTPBadRequest as exc:
        return exc

    consent_key = data.get("consent_key")
    if not consent_key:
        return HTTPBadRequest(
            content={"error": "invalid_request", "error_description": "consent_key is required"}
        )

    consents = {c["consent_key"]: c for c in await store.list_consents(user.id)}
    consent = consents.get(consent_key)
    if consent is None:
        return HTTPNotFound(content={"error": "not_found", "error_description": "unknown consent"})

    await store.delete_consent(consent_key, user_id=user.id)
    # Complete deauthorization: revoke every refresh token this user holds for
    # the client so revoking consent also kills active sessions.
    await store.revoke_user_client_refresh_tokens(user_id=user.id, client_id=consent["client_id"])
    return {}

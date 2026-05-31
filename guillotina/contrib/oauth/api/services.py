from guillotina import app_settings, configure
from guillotina.api.service import Service
from guillotina.auth.utils import set_authenticated_user
from guillotina.contrib.oauth.api.request import (
    client_identifier,
    form_content_type_valid,
    normalize_list,
    parse_form_encoded,
    reject_duplicate_params,
)
from guillotina.contrib.oauth.api.urls import container_url, validate_resource
from guillotina.contrib.oauth.api.views import consent_form, login_form, oauth_error_page
from guillotina.contrib.oauth.api.well_known import rfc_well_known_response
from guillotina.contrib.oauth.flow.clients import (
    consent_key,
    make_client,
    redirect_uri_registered_for_client,
    redirect_with_params,
)
from guillotina.contrib.oauth.flow.csrf import OAUTH_CSRF_FIELD, csrf_valid
from guillotina.contrib.oauth.flow.pkce import pkce_challenge_valid, verify_s256
from guillotina.contrib.oauth.flow.ratelimit import rate_limit_exceeded
from guillotina.contrib.oauth.flow.scopes import OAUTH_DEFAULT_SCOPE, oauth_scopes_supported
from guillotina.contrib.oauth.flow.tokens import issue_access_token, opaque_token, token_hash
from guillotina.contrib.oauth.storage.access import get_oauth_store
from guillotina.interfaces import IApplication, IContainer
from guillotina.response import HTTPBadRequest, HTTPFound, HTTPNotFound, HTTPTooManyRequests, Response
from guillotina.utils import get_authenticated_user


WELL_KNOWN_HANDLERS = {}
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


def register_well_known_handler(name, handler):
    WELL_KNOWN_HANDLERS[name] = handler


def _metadata(request, container):
    issuer = container_url(request, container)
    return {
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/oauth/authorize",
        "token_endpoint": f"{issuer}/oauth/token",
        "registration_endpoint": f"{issuer}/oauth/register",
        "revocation_endpoint": f"{issuer}/oauth/revoke",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "revocation_endpoint_auth_methods_supported": ["none"],
        "resource_indicators_supported": True,
        "scopes_supported": oauth_scopes_supported(),
    }


register_well_known_handler("oauth-authorization-server", _metadata)
# Compatibility alias: some clients probe `openid-configuration`; payload is OAuth AS metadata, not full OIDC.
register_well_known_handler("openid-configuration", _metadata)


class OAuthService(Service):
    def oauth_store(self):
        return get_oauth_store(self.context)


@configure.service(
    context=IContainer,
    method="GET",
    permission="guillotina.Public",
    name=".well-known/{action}",
    allow_access=True,
)
class OAuthWellKnown(OAuthService):
    async def __call__(self):
        self.oauth_store()
        action = self.request.matchdict.get("action", "")
        if action in WELL_KNOWN_HANDLERS:
            return WELL_KNOWN_HANDLERS[action](self.request, self.context)
        return HTTPNotFound(content={"reason": f"Unknown well-known endpoint: {action}"})


@configure.service(
    context=IApplication,
    method="GET",
    permission="guillotina.Public",
    name=".well-known/{action}/{target_path:path}",
    allow_access=True,
)
class OAuthRFCWellKnown(Service):
    async def __call__(self):
        action = self.request.matchdict.get("action", "")
        if action not in WELL_KNOWN_HANDLERS:
            return HTTPNotFound(content={"reason": f"Unknown well-known endpoint: {action}"})
        target_path = self.request.matchdict.get("target_path", "")
        try:
            return await rfc_well_known_response(self.request, action, target_path, WELL_KNOWN_HANDLERS)
        except HTTPNotFound as exc:
            return exc


@configure.service(
    context=IContainer,
    method="GET",
    permission="guillotina.Public",
    name="oauth/{action}",
    allow_access=True,
)
class OAuthGet(OAuthService):
    async def __call__(self):
        action = self.request.matchdict.get("action", "")
        if action == "authorize":
            return await _authorize(self, self.oauth_store())
        return HTTPNotFound(content={"reason": f"Unknown OAuth GET action: {action}"})


@configure.service(
    context=IContainer,
    method="POST",
    permission="guillotina.Public",
    name="oauth/{action}",
    allow_access=True,
)
class OAuthPost(OAuthService):
    async def __call__(self):
        store = self.oauth_store()
        action = self.request.matchdict.get("action", "")
        if action == "register":
            return await _register(self, store)
        if action == "authorize":
            return await _authorize(self, store)
        if action == "token":
            return await _token(self, store)
        if action == "revoke":
            return await _revoke(self, store)
        return HTTPNotFound(content={"reason": f"Unknown OAuth POST action: {action}"})


async def _register(service, store):
    oauth_settings = app_settings.get("oauth", {})
    if rate_limit_exceeded(
        f"oauth-register:{client_identifier(service.request)}",
        limit=oauth_settings.get("registration_rate_limit", 20),
        window=oauth_settings.get("registration_rate_window", 600),
    ):
        return HTTPTooManyRequests(
            content={
                "error": "temporarily_unavailable",
                "error_description": "client registration rate limit exceeded",
            }
        )
    data = await service.request.json()
    try:
        client = make_client(data)
    except HTTPBadRequest as exc:
        return exc
    await store.create_client(client)
    return {
        key: client[key]
        for key in (
            "client_id",
            "client_name",
            "redirect_uris",
            "grant_types",
            "response_types",
            "token_endpoint_auth_method",
        )
    }


async def _authenticate_basic(username, password):
    creds = {"type": "basic", "token": password, "id": username}
    for validator in app_settings["auth_token_validators"]:
        if validator.for_validators is not None and "basic" not in validator.for_validators:
            continue
        user = await validator().validate(creds)
        if user is not None:
            set_authenticated_user(user)
            return user


def _token_response(content):
    return Response(
        content=content,
        headers={
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
        },
    )


async def _authorize(service, store):
    params = dict(service.request.query)
    try:
        reject_duplicate_params(service.request.query, AUTHORIZE_SINGLETON_PARAMS)
    except HTTPBadRequest as exc:
        return exc
    if service.request.method == "POST":
        content_type = service.request.headers.get("content-type", "")
        if "application/json" in content_type:
            data = await service.request.json()
        else:
            try:
                data = parse_form_encoded(
                    await service.request.text(), singleton_fields=AUTHORIZE_SINGLETON_PARAMS
                )
            except HTTPBadRequest as exc:
                return exc
        params.update(data)
    client = await store.get_client(params.get("client_id"))
    if client is None:
        return oauth_error_page("Unknown OAuth client", "The application is not registered.", status=400)
    redirect_uri = params.get("redirect_uri")
    if not redirect_uri_registered_for_client(client, redirect_uri):
        return oauth_error_page(
            "Invalid redirect URI",
            "The requested redirect URI is not allowed for this OAuth client.",
            status=400,
        )
    if params.get("response_type") != "code":
        return HTTPFound(
            redirect_with_params(
                redirect_uri, {"error": "unsupported_response_type", "state": params.get("state")}
            )
        )
    if "code" not in set(client.get("response_types") or []):
        return HTTPFound(
            redirect_with_params(redirect_uri, {"error": "unauthorized_client", "state": params.get("state")})
        )
    require_pkce = app_settings.get("oauth", {}).get("require_pkce", True)
    allowed_methods = app_settings.get("oauth", {}).get("allowed_code_challenge_methods", ["S256"])
    code_challenge = params.get("code_challenge")
    code_challenge_method = params.get("code_challenge_method")

    if require_pkce and not code_challenge:
        return HTTPFound(
            redirect_with_params(redirect_uri, {"error": "invalid_request", "state": params.get("state")})
        )
    if code_challenge and not pkce_challenge_valid(code_challenge):
        return HTTPFound(
            redirect_with_params(redirect_uri, {"error": "invalid_request", "state": params.get("state")})
        )
    if code_challenge and code_challenge_method not in allowed_methods:
        return HTTPFound(
            redirect_with_params(redirect_uri, {"error": "invalid_request", "state": params.get("state")})
        )
    scopes = normalize_list(params.get("scope"))
    supported_scopes = set(oauth_scopes_supported())
    if not scopes or OAUTH_DEFAULT_SCOPE not in scopes or not set(scopes).issubset(supported_scopes):
        return HTTPFound(
            redirect_with_params(redirect_uri, {"error": "invalid_scope", "state": params.get("state")})
        )
    try:
        resources = validate_resource(service.request, service.context, params.get("resource"))
    except HTTPBadRequest:
        return HTTPFound(
            redirect_with_params(redirect_uri, {"error": "invalid_target", "state": params.get("state")})
        )
    user = get_authenticated_user()
    newly_authenticated_token = None
    authenticated_on_this_request = False
    if user is None or getattr(user, "id", "Anonymous User") == "Anonymous User":
        if service.request.method == "POST" and params.get("username"):
            user = await _authenticate_basic(params.get("username"), params.get("password", ""))
            if user is None:
                return oauth_error_page(
                    "Login failed",
                    "The username or password could not be verified.",
                    status=401,
                )
            from guillotina.auth import authenticate_user

            newly_authenticated_token, _ = authenticate_user(user.id)
            authenticated_on_this_request = True
        else:
            return login_form(params, client)
    response_obj = None
    ckey = consent_key(user.id, client["client_id"], scopes, resources)
    existing_consent = await store.has_consent(ckey)
    decision = (
        params.get("decision")
        if service.request.method == "POST" and not authenticated_on_this_request
        else None
    )
    if decision in ("allow", "deny") and not csrf_valid(
        params.get(OAUTH_CSRF_FIELD), params, user.id, scopes, resources
    ):
        response_obj = HTTPFound(
            redirect_with_params(redirect_uri, {"error": "invalid_request", "state": params.get("state")})
        )
    elif not existing_consent and decision != "allow":
        if decision == "deny":
            response_obj = HTTPFound(
                redirect_with_params(redirect_uri, {"error": "access_denied", "state": params.get("state")})
            )
        else:
            response_obj = consent_form(params, client, scopes, resources, user)
    else:
        if not existing_consent:
            await store.create_consent(
                ckey,
                user_id=user.id,
                client_id=client["client_id"],
                scope=scopes,
                resource=resources,
            )
        raw_code = opaque_token("goc_")
        await store.create_code(
            raw_code=raw_code,
            client_id=client["client_id"],
            user_id=user.id,
            redirect_uri=redirect_uri,
            scope=scopes,
            resource=resources,
            code_challenge=params.get("code_challenge"),
        )
        response_obj = HTTPFound(
            redirect_with_params(redirect_uri, {"code": raw_code, "state": params.get("state")})
        )

    if newly_authenticated_token is not None:
        secure = ""
        if str(getattr(service.request, "scheme", "") or "").lower() == "https":
            secure = "; Secure"
        response_obj.headers["Set-Cookie"] = (
            f"auth_token={newly_authenticated_token}; Path=/; HttpOnly; SameSite=Lax{secure}"
        )
    return response_obj


async def _token(service, store):
    if not form_content_type_valid(service.request):
        return HTTPBadRequest(
            content={"error": "invalid_request", "error_description": "invalid content type"}
        )
    try:
        data = parse_form_encoded(await service.request.text(), singleton_fields=TOKEN_SINGLETON_PARAMS)
    except HTTPBadRequest as exc:
        return exc
    grant_type = data.get("grant_type")
    if grant_type == "authorization_code":
        return await _authorization_code(service, store, data)
    if grant_type == "refresh_token":
        return await _refresh_token(service, store, data)
    return HTTPBadRequest(content={"error": "unsupported_grant_type"})


async def _authorization_code(service, store, data):
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
    require_pkce = app_settings.get("oauth", {}).get("require_pkce", True)
    if record.get("code_challenge"):
        if not verify_s256(data.get("code_verifier", ""), record["code_challenge"]):
            return HTTPBadRequest(content={"error": "invalid_grant"})
    elif require_pkce:
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
    return _token_response(
        {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": app_settings["oauth"].get("access_token_ttl", 3600),
            "refresh_token": refresh_token,
            "scope": " ".join(record["scope"]),
        }
    )


async def _refresh_token(service, store, data):
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
    return _token_response(
        {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": app_settings["oauth"].get("access_token_ttl", 3600),
            "refresh_token": new_refresh,
            "scope": " ".join(scopes),
        }
    )


async def _revoke(service, store):
    if not form_content_type_valid(service.request):
        return HTTPBadRequest(
            content={"error": "invalid_request", "error_description": "invalid content type"}
        )
    try:
        data = parse_form_encoded(await service.request.text(), singleton_fields=REVOKE_SINGLETON_PARAMS)
    except HTTPBadRequest as exc:
        return exc
    record = await store.get_refresh_token(data.get("token", ""))
    if record is not None and record.get("client_id") == data.get("client_id"):
        await store.revoke_refresh_family(
            client_id=record["client_id"],
            user_id=record["user_id"],
            auth_code_hash=record.get("auth_code_hash"),
        )
    return {}

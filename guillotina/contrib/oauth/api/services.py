from base64 import b64encode
from functools import lru_cache
from html import escape as html_escape
from pathlib import Path
from string import Template

from guillotina import app_settings, configure
from guillotina.api.service import Service
from guillotina.auth.utils import set_authenticated_user
from guillotina.contrib.oauth.api.request import normalize_list, parse_form_encoded
from guillotina.contrib.oauth.api.urls import container_url, validate_resource
from guillotina.contrib.oauth.api.well_known import rfc_well_known_response
from guillotina.contrib.oauth.flow.clients import (
    consent_key,
    make_client,
    redirect_uri_registered_for_client,
    redirect_with_params,
)
from guillotina.contrib.oauth.flow.pkce import verify_s256
from guillotina.contrib.oauth.flow.scopes import OAUTH_SCOPE_DESCRIPTIONS, oauth_scopes_supported
from guillotina.contrib.oauth.flow.tokens import issue_access_token, opaque_token, token_hash
from guillotina.contrib.oauth.storage.access import get_oauth_store
from guillotina.interfaces import IApplication, IContainer
from guillotina.response import HTTPBadRequest, HTTPFound, HTTPNotFound, Response
from guillotina.utils import get_authenticated_user


WELL_KNOWN_HANDLERS = {}
TEMPLATE_DIR = Path(__file__).parent / "templates"
BRAND_LOGO_PATH = Path(__file__).parents[3] / "static" / "assets" / "brand" / "guillotina-logo-horizontal.svg"


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


def _html(body, status=200):
    return Response(body=body.encode("utf-8"), status=status, content_type="text/html")


@lru_cache(maxsize=None)
def _template(name):
    return Template((TEMPLATE_DIR / name).read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def _template_text(name):
    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


@lru_cache(maxsize=None)
def _logo_data_uri():
    encoded = b64encode(BRAND_LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def _render_template(template_name, **context):
    return _template(template_name).substitute(context)


def _oauth_page(title, heading, body, *, status=200, tone="default"):
    return _html(
        _render_template(
            "base.html",
            title=html_escape(title),
            logo_src=_logo_data_uri(),
            style=_template_text("oauth.css"),
            tone=html_escape(tone),
            heading=html_escape(heading),
            body=body,
        ),
        status=status,
    )


def _hidden_inputs(params):
    fields = (
        "response_type",
        "client_id",
        "redirect_uri",
        "scope",
        "state",
        "code_challenge",
        "code_challenge_method",
        "resource",
    )
    html = []
    for field in fields:
        value = params.get(field)
        if value is None:
            continue
        values = value if isinstance(value, list) else [value]
        for item in values:
            html.append(
                _render_template(
                    "hidden_input.html",
                    name=html_escape(field, quote=True),
                    value=html_escape(str(item), quote=True),
                )
            )
    return "\n".join(html)


def _oauth_error_page(title, message, *, status):
    return _oauth_page(
        title,
        title,
        _render_template("error.html", message=html_escape(message)),
        status=status,
        tone="error",
    )


def _login_form(params, client):
    client_name = html_escape(client.get("client_name") or client["client_id"])
    body = _render_template(
        "login.html",
        client_name=client_name,
        client_id=html_escape(client["client_id"]),
        redirect_uri=html_escape(params.get("redirect_uri", "")),
        hidden_inputs=_hidden_inputs(params),
    )
    return _oauth_page("Login to Guillotina", "Login required", body)


def _list_items(values, *, empty):
    if not values:
        return _render_template("plain_item.html", value=html_escape(empty))
    return "".join(_render_template("list_item.html", value=html_escape(str(value))) for value in values)


def _scope_items(scopes):
    if not scopes:
        return _render_template("plain_item.html", value="No extra scopes were requested.")
    return "".join(
        _render_template(
            "scope_item.html",
            scope=html_escape(str(scope)),
            description=html_escape(
                OAUTH_SCOPE_DESCRIPTIONS.get(scope, "Access requested by this OAuth client.")
            ),
        )
        for scope in scopes
    )


def _consent_form(params, client, scopes, resources, user):
    raw_client_name = client.get("client_name") or client["client_id"]
    client_name = html_escape(raw_client_name)
    body = _render_template(
        "consent.html",
        client_name=client_name,
        user_id=html_escape(str(user.id)),
        client_id=html_escape(client["client_id"]),
        redirect_uri=html_escape(params.get("redirect_uri", "")),
        scope_items=_scope_items(scopes),
        resource_items=_list_items(resources, empty="Default Guillotina container"),
        hidden_inputs=_hidden_inputs(params),
    )
    return _oauth_page("Authorize OAuth Client", f"Allow {raw_client_name}?", body)


async def _authorize(service, store):
    params = dict(service.request.query)
    if service.request.method == "POST":
        content_type = service.request.headers.get("content-type", "")
        if "application/json" in content_type:
            data = await service.request.json()
        else:
            data = parse_form_encoded(await service.request.text())
        params.update(data)
    client = await store.get_client(params.get("client_id"))
    if client is None:
        return _oauth_error_page("Unknown OAuth client", "The application is not registered.", status=400)
    redirect_uri = params.get("redirect_uri")
    if not redirect_uri_registered_for_client(client, redirect_uri):
        return _oauth_error_page(
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
    require_pkce = app_settings.get("oauth", {}).get("require_pkce", True)
    allowed_methods = app_settings.get("oauth", {}).get("allowed_code_challenge_methods", ["S256"])
    code_challenge = params.get("code_challenge")
    code_challenge_method = params.get("code_challenge_method")

    if require_pkce and not code_challenge:
        return HTTPFound(
            redirect_with_params(redirect_uri, {"error": "invalid_request", "state": params.get("state")})
        )
    if code_challenge and code_challenge_method not in allowed_methods:
        return HTTPFound(
            redirect_with_params(redirect_uri, {"error": "invalid_request", "state": params.get("state")})
        )
    scopes = normalize_list(params.get("scope"))
    supported_scopes = set(oauth_scopes_supported())
    if scopes and not set(scopes).issubset(supported_scopes):
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
    if user is None or getattr(user, "id", "Anonymous User") == "Anonymous User":
        if service.request.method == "POST" and params.get("username"):
            user = await _authenticate_basic(params.get("username"), params.get("password", ""))
            if user is None:
                return _oauth_error_page(
                    "Login failed",
                    "The username or password could not be verified.",
                    status=401,
                )
            from guillotina.auth import authenticate_user

            newly_authenticated_token, _ = authenticate_user(user.id)
        else:
            return _login_form(params, client)
    response_obj = None
    ckey = consent_key(user.id, client["client_id"], scopes, resources)
    if not await store.has_consent(ckey) and params.get("decision") != "allow":
        if params.get("decision") == "deny":
            response_obj = HTTPFound(
                redirect_with_params(redirect_uri, {"error": "access_denied", "state": params.get("state")})
            )
        else:
            response_obj = _consent_form(params, client, scopes, resources, user)
    else:
        if not await store.has_consent(ckey):
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
    data = parse_form_encoded(await service.request.text())
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
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": app_settings["oauth"].get("access_token_ttl", 3600),
        "refresh_token": refresh_token,
        "scope": " ".join(record["scope"]),
    }


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
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": app_settings["oauth"].get("access_token_ttl", 3600),
        "refresh_token": new_refresh,
        "scope": " ".join(scopes),
    }


async def _revoke(service, store):
    data = parse_form_encoded(await service.request.text())
    record = await store.get_refresh_token(data.get("token", ""))
    if record is not None and record.get("client_id") == data.get("client_id"):
        await store.delete_refresh_token(data.get("token", ""))
    return {}

from datetime import timedelta

from guillotina import app_settings, configure
from guillotina.api.service import Service
from guillotina.auth.utils import set_authenticated_user
from guillotina.contrib.oauth.pkce import verify_s256
from guillotina.contrib.oauth.tokens import issue_access_token, opaque_token, token_hash, utcnow
from guillotina.contrib.oauth.utils import (
    consent_key,
    container_url,
    create_code,
    get_storage,
    get_valid_code,
    get_valid_refresh,
    make_client,
    normalize_list,
    oauth_error,
    parse_form_encoded,
    redirect_with_params,
    register_changed,
    validate_resource,
)
from guillotina.interfaces import IContainer
from guillotina.response import HTTPBadRequest, HTTPFound, HTTPNotFound, Response
from guillotina.utils import get_authenticated_user


OAUTH_SCOPES = ["guillotina:mcp.read", "guillotina:mcp.search", "guillotina:mcp.content.read"]


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
        "scopes_supported": app_settings.get("oauth", {}).get("scopes_supported", OAUTH_SCOPES),
    }


def _protected_resource_metadata(request, container):
    issuer = container_url(request, container)
    return {
        "resource": f"{issuer}/@mcp/protocol",
        "authorization_servers": [issuer],
        "scopes_supported": OAUTH_SCOPES,
    }


class OAuthService(Service):
    async def storage(self):
        return await get_storage(self.context)


@configure.service(
    context=IContainer,
    method="GET",
    permission="guillotina.Public",
    name=".well-known/{action}",
    allow_access=True,
)
class OAuthWellKnown(OAuthService):
    async def __call__(self):
        await self.storage()
        action = self.request.matchdict.get("action", "")
        if action in ("oauth-authorization-server", "openid-configuration"):
            return _metadata(self.request, self.context)
        if action == "oauth-protected-resource":
            return _protected_resource_metadata(self.request, self.context)
        raise HTTPNotFound(content={"reason": f"Unknown well-known endpoint: {action}"})


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
            return await _authorize(self, await self.storage())
        raise HTTPNotFound(content={"reason": f"Unknown OAuth GET action: {action}"})


@configure.service(
    context=IContainer,
    method="POST",
    permission="guillotina.Public",
    name="oauth/{action}",
    allow_access=True,
)
class OAuthPost(OAuthService):
    async def __call__(self):
        storage = await self.storage()
        action = self.request.matchdict.get("action", "")
        if action == "register":
            return await _register(self, storage)
        if action == "authorize":
            return await _authorize(self, storage)
        if action == "token":
            return await _token(self, storage)
        if action == "revoke":
            return await _revoke(self, storage)
        raise HTTPNotFound(content={"reason": f"Unknown OAuth POST action: {action}"})


async def _register(service, storage):
    data = await service.request.json()
    client = make_client(data)
    if client["client_id"] in storage["clients"]:
        oauth_error("invalid_request", "client_id already exists")
    storage["clients"][client["client_id"]] = client
    register_changed(storage)
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


async def _authorize(service, storage):
    params = dict(service.request.query)
    if service.request.method == "POST":
        content_type = service.request.headers.get("content-type", "")
        if "application/json" in content_type:
            data = await service.request.json()
        else:
            data = parse_form_encoded(await service.request.text())
        params.update(data)
    client = storage["clients"].get(params.get("client_id"))
    if client is None:
        return _html("Unknown OAuth client", status=400)
    redirect_uri = params.get("redirect_uri")
    if redirect_uri not in client["redirect_uris"]:
        return _html("Invalid redirect_uri", status=400)
    if params.get("response_type") != "code":
        raise HTTPBadRequest(content={"error": "unsupported_response_type"})
    if not params.get("code_challenge"):
        return HTTPFound(redirect_with_params(redirect_uri, {"error": "invalid_request", "state": params.get("state")}))
    if params.get("code_challenge_method") != "S256":
        return HTTPFound(redirect_with_params(redirect_uri, {"error": "invalid_request", "state": params.get("state")}))
    scopes = normalize_list(params.get("scope"))
    resources = validate_resource(service.request, service.context, params.get("resource"))
    user = get_authenticated_user()
    if user is None or getattr(user, "id", "Anonymous User") == "Anonymous User":
        if service.request.method == "POST" and params.get("username"):
            user = await _authenticate_basic(params.get("username"), params.get("password", ""))
            if user is None:
                return _html("Login failed", status=401)
        else:
            return _html(
                "<form method='post'>Username <input name='username'>Password "
                "<input name='password' type='password'><button>Login</button></form>"
            )
    ckey = consent_key(user.id, client["client_id"], scopes, resources)
    if ckey not in storage["consents"] and params.get("decision") != "allow":
        if params.get("decision") == "deny":
            return HTTPFound(redirect_with_params(redirect_uri, {"error": "access_denied", "state": params.get("state")}))
        return _html(
            "<form method='post'><p>Allow {}</p><button name='decision' value='allow'>Allow</button>"
            "<button name='decision' value='deny'>Deny</button></form>".format(client["client_name"])
        )
    if ckey not in storage["consents"]:
        storage["consents"][ckey] = {
            "user_id": user.id,
            "client_id": client["client_id"],
            "scope": scopes,
            "resource": resources,
            "granted_at": utcnow().isoformat(),
        }
    raw_code = opaque_token("goc_")
    create_code(
        storage,
        raw_code=raw_code,
        client_id=client["client_id"],
        user_id=user.id,
        redirect_uri=redirect_uri,
        scope=scopes,
        resource=resources,
        code_challenge=params["code_challenge"],
    )
    register_changed(storage)
    return HTTPFound(redirect_with_params(redirect_uri, {"code": raw_code, "state": params.get("state")}))


async def _token(service, storage):
    data = parse_form_encoded(await service.request.text())
    grant_type = data.get("grant_type")
    if grant_type == "authorization_code":
        return _authorization_code(service, storage, data)
    if grant_type == "refresh_token":
        return _refresh_token(service, storage, data)
    raise HTTPBadRequest(content={"error": "unsupported_grant_type"})


def _authorization_code(service, storage, data):
    client = storage["clients"].get(data.get("client_id"))
    record = get_valid_code(storage, data.get("code", ""))
    if client is None or record is None:
        raise HTTPBadRequest(content={"error": "invalid_grant"})
    if record["client_id"] != client["client_id"] or record["redirect_uri"] != data.get("redirect_uri"):
        raise HTTPBadRequest(content={"error": "invalid_grant"})
    if not verify_s256(data.get("code_verifier", ""), record["code_challenge"]):
        raise HTTPBadRequest(content={"error": "invalid_grant"})
    requested_resources = normalize_list(data.get("resource"))
    if requested_resources and not set(requested_resources).issubset(set(record["resource"])):
        raise HTTPBadRequest(content={"error": "invalid_target"})
    resources = requested_resources or record["resource"]
    record["used_at"] = utcnow().isoformat()
    access_token, _claims = issue_access_token(
        issuer=container_url(service.request, service.context),
        subject=record["user_id"],
        audience=resources,
        client_id=client["client_id"],
        scope=record["scope"],
    )
    refresh_token = opaque_token("gor_")
    now = utcnow()
    storage["refresh_tokens"][token_hash(refresh_token)] = {
        "token_hash": token_hash(refresh_token),
        "client_id": client["client_id"],
        "user_id": record["user_id"],
        "scope": record["scope"],
        "resource": resources,
        "expires_at": (now + timedelta(seconds=app_settings["oauth"].get("refresh_token_ttl", 2592000))).isoformat(),
        "revoked_at": None,
        "rotated_from": None,
        "created_at": now.isoformat(),
        "last_used_at": now.isoformat(),
    }
    register_changed(storage)
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": app_settings["oauth"].get("access_token_ttl", 3600),
        "refresh_token": refresh_token,
        "scope": " ".join(record["scope"]),
    }


def _refresh_token(service, storage, data):
    record = get_valid_refresh(storage, data.get("refresh_token", ""))
    client = storage["clients"].get(data.get("client_id"))
    if record is None or client is None or record["client_id"] != client["client_id"]:
        raise HTTPBadRequest(content={"error": "invalid_grant"})
    scopes = normalize_list(data.get("scope")) or record["scope"]
    resources = normalize_list(data.get("resource")) or record["resource"]
    if not set(scopes).issubset(set(record["scope"])) or not set(resources).issubset(set(record["resource"])):
        raise HTTPBadRequest(content={"error": "invalid_scope"})
    record["revoked_at"] = utcnow().isoformat()
    new_refresh = opaque_token("gor_")
    now = utcnow()
    storage["refresh_tokens"][token_hash(new_refresh)] = {
        **record,
        "token_hash": token_hash(new_refresh),
        "scope": scopes,
        "resource": resources,
        "revoked_at": None,
        "rotated_from": record["token_hash"],
        "created_at": now.isoformat(),
        "last_used_at": now.isoformat(),
    }
    access_token, _claims = issue_access_token(
        issuer=container_url(service.request, service.context),
        subject=record["user_id"],
        audience=resources,
        client_id=client["client_id"],
        scope=scopes,
    )
    register_changed(storage)
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": app_settings["oauth"].get("access_token_ttl", 3600),
        "refresh_token": new_refresh,
        "scope": " ".join(scopes),
    }


async def _revoke(service, storage):
    data = parse_form_encoded(await service.request.text())
    record = storage["refresh_tokens"].get(token_hash(data.get("token", "")))
    if record is not None and record.get("client_id") == data.get("client_id"):
        record["revoked_at"] = utcnow().isoformat()
        register_changed(storage)
    return {}

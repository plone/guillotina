from datetime import timedelta
from urllib.parse import parse_qs, urlencode, urlparse
from uuid import uuid4

from guillotina import app_settings, task_vars
from guillotina.interfaces import WRITING_VERBS
from guillotina.contrib.oauth.content import OAUTH_STORAGE_KEY, new_oauth_storage
from guillotina.contrib.oauth.tokens import token_hash, utcnow
from guillotina.interfaces import IAddons, IAnnotations
from guillotina.response import HTTPBadRequest, HTTPPreconditionFailed


def check_writable_request(request):
    return request.method in WRITING_VERBS or (
        request.method == "GET" and str(getattr(request, "path", "")).endswith("/oauth/authorize")
    )


def container_url(request, container):
    issuer = app_settings.get("oauth", {}).get("issuer")
    if issuer:
        return issuer.rstrip("/")
    return f"{request.scheme}://{request.host}/db/{container.id}"


def mcp_resource(request, container):
    return f"{container_url(request, container)}/@mcp/protocol"


def normalize_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        values = []
        for item in value:
            values.extend(normalize_list(item))
        return values
    return [item for item in str(value).split() if item]


def parse_form_encoded(body):
    parsed = parse_qs(body, keep_blank_values=True)
    return {key: values if len(values) > 1 else values[0] for key, values in parsed.items()}


def oauth_error(error, description=None, status=400):
    content = {"error": error}
    if description:
        content["error_description"] = description
    raise HTTPBadRequest(content=content) if status == 400 else HTTPPreconditionFailed(content=content)


def is_installed(container):
    registry = task_vars.registry.get(None)
    if registry is None:
        return False
    try:
        return "oauth" in registry.for_interface(IAddons)["enabled"]
    except Exception:
        return False


async def get_storage(container, *, require_installed=True):
    if require_installed and not is_installed(container):
        raise HTTPPreconditionFailed(content={"reason": "OAuth addon is not installed"})
    annotations = IAnnotations(container)
    storage = await annotations.async_get(OAUTH_STORAGE_KEY)
    if storage is None:
        storage = new_oauth_storage()
        await annotations.async_set(OAUTH_STORAGE_KEY, storage)
    return storage


def register_changed(storage):
    txn = getattr(storage, "__txn__", None)
    if txn is not None:
        txn.register(storage)


def validate_redirect_uri(uri):
    if not uri:
        return False
    if "*" in uri:
        return False
    parsed = urlparse(uri)
    if parsed.scheme in ("javascript", "data"):
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    if not parsed.netloc:
        return False
    return True


def make_client(data):
    redirect_uris = data.get("redirect_uris") or []
    if not redirect_uris or not isinstance(redirect_uris, list):
        oauth_error("invalid_request", "redirect_uris is required")
    if any(not validate_redirect_uri(uri) for uri in redirect_uris):
        oauth_error("invalid_request", "unsafe redirect_uri")
    method = data.get("token_endpoint_auth_method", "none")
    if method != "none":
        oauth_error("unsupported_token_endpoint_auth_method")
    now = utcnow().isoformat()
    return {
        "client_id": data.get("client_id") or uuid4().hex,
        "client_name": data.get("client_name") or "OAuth Client",
        "redirect_uris": redirect_uris,
        "grant_types": data.get("grant_types") or ["authorization_code", "refresh_token"],
        "response_types": data.get("response_types") or ["code"],
        "token_endpoint_auth_method": "none",
        "scope": " ".join(normalize_list(data.get("scope"))),
        "created_at": now,
        "updated_at": now,
    }


def consent_key(user_id, client_id, scopes, resources):
    return "|".join([user_id, client_id, " ".join(sorted(scopes)), " ".join(sorted(resources))])


def redirect_with_params(uri, params):
    sep = "&" if "?" in uri else "?"
    return f"{uri}{sep}{urlencode({k: v for k, v in params.items() if v is not None})}"


def validate_resource(request, container, resources):
    base = container_url(request, container)
    allowed = {base, f"{base}/@mcp/protocol"}
    if not resources:
        return [base]
    resources = normalize_list(resources)
    for resource in resources:
        if resource not in allowed:
            oauth_error("invalid_target", "resource is not allowed")
    return resources


def create_code(storage, *, raw_code, client_id, user_id, redirect_uri, scope, resource, code_challenge):
    now = utcnow()
    ttl = app_settings["oauth"].get("authorization_code_ttl", 600)
    code_record = {
        "code_hash": token_hash(raw_code),
        "client_id": client_id,
        "user_id": user_id,
        "redirect_uri": redirect_uri,
        "scope": list(scope),
        "resource": list(resource),
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "expires_at": (now + timedelta(seconds=ttl)).isoformat(),
        "used_at": None,
        "created_at": now.isoformat(),
    }
    storage["codes"][code_record["code_hash"]] = code_record
    register_changed(storage)
    return code_record


def get_valid_code(storage, code):
    record = storage["codes"].get(token_hash(code))
    if record is None or record.get("used_at"):
        return None
    if utcnow().isoformat() > record["expires_at"]:
        return None
    return record


def get_valid_refresh(storage, token):
    record = storage["refresh_tokens"].get(token_hash(token))
    if record is None or record.get("revoked_at"):
        return None
    if utcnow().isoformat() > record["expires_at"]:
        return None
    return record

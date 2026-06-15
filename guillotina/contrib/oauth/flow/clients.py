from urllib.parse import urlencode, urlparse
from uuid import uuid4

from guillotina.contrib.oauth.flow.scopes import OAUTH_DEFAULT_SCOPE, oauth_scopes_supported
from guillotina.contrib.oauth.utils.errors import raise_oauth_error
from guillotina.contrib.oauth.utils.request import normalize_list
from guillotina.contrib.oauth.utils.time import timestamp, utcnow


SUPPORTED_GRANT_TYPES = {"authorization_code", "refresh_token"}
SUPPORTED_RESPONSE_TYPES = {"code"}
LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _is_loopback_http_redirect(parsed):
    return parsed.scheme == "http" and parsed.hostname in LOOPBACK_HOSTS and parsed.path.startswith("/")


def _is_private_use_redirect(parsed):
    if parsed.scheme in ("http", "https", "javascript", "data"):
        return False
    if not parsed.path.startswith("/"):
        return False
    if "." in parsed.scheme:
        return True
    return parsed.scheme.isalpha() and bool(parsed.netloc)


def validate_redirect_uri(uri):
    if not uri:
        return False
    if "*" in uri:
        return False
    parsed = urlparse(uri)
    if parsed.fragment:
        return False
    if parsed.scheme in ("javascript", "data"):
        return False
    if parsed.scheme == "https":
        return bool(parsed.netloc and parsed.path.startswith("/"))
    if _is_loopback_http_redirect(parsed):
        return True
    return _is_private_use_redirect(parsed)


def redirect_uri_registered_for_client(client, redirect_uri):
    """Return True only if redirect_uri was registered for this client (no side effects).

    Native redirects must be included in the client's dynamic registration request.
    """
    redirect_uris = client.get("redirect_uris") or []
    if redirect_uri in redirect_uris:
        return True
    requested = urlparse(redirect_uri or "")
    if not _is_loopback_http_redirect(requested):
        return False
    for registered_uri in redirect_uris:
        registered = urlparse(registered_uri)
        if not _is_loopback_http_redirect(registered):
            continue
        if (
            requested.scheme == registered.scheme
            and requested.hostname == registered.hostname
            and requested.path == registered.path
            and requested.query == registered.query
        ):
            return True
    return False


def build_client_from_registration(data):
    if data.get("client_id"):
        raise_oauth_error("invalid_request", "client_id is server-issued")
    redirect_uris = data.get("redirect_uris") or []
    if not redirect_uris or not isinstance(redirect_uris, list):
        raise_oauth_error("invalid_client_metadata", "redirect_uris is required")
    if any(not validate_redirect_uri(uri) for uri in redirect_uris):
        raise_oauth_error("invalid_redirect_uri", "unsafe redirect_uri")
    method = data.get("token_endpoint_auth_method", "none")
    if method != "none":
        raise_oauth_error("unsupported_token_endpoint_auth_method")
    grant_types = data["grant_types"] if "grant_types" in data else ["authorization_code", "refresh_token"]
    response_types = data["response_types"] if "response_types" in data else ["code"]
    if not isinstance(grant_types, list) or not grant_types:
        raise_oauth_error("invalid_client_metadata", "grant_types must be a non-empty array")
    if not isinstance(response_types, list) or not response_types:
        raise_oauth_error("invalid_client_metadata", "response_types must be a non-empty array")
    if any(grant_type not in SUPPORTED_GRANT_TYPES for grant_type in grant_types):
        raise_oauth_error("invalid_client_metadata", "unsupported grant_type")
    if any(response_type not in SUPPORTED_RESPONSE_TYPES for response_type in response_types):
        raise_oauth_error("invalid_client_metadata", "unsupported response_type")
    if "authorization_code" in grant_types and "code" not in response_types:
        raise_oauth_error("invalid_client_metadata", "authorization_code grant requires code response_type")
    if "code" in response_types and "authorization_code" not in grant_types:
        raise_oauth_error("invalid_client_metadata", "code response_type requires authorization_code grant")
    scope = normalize_list(data.get("scope")) or [OAUTH_DEFAULT_SCOPE]
    if OAUTH_DEFAULT_SCOPE not in scope:
        raise_oauth_error("invalid_client_metadata", f"{OAUTH_DEFAULT_SCOPE} scope is required")
    if not set(scope).issubset(set(oauth_scopes_supported())):
        raise_oauth_error("invalid_client_metadata", "unsupported scope")
    now_dt = utcnow()
    now = now_dt.isoformat()
    return {
        "client_id": uuid4().hex,
        "client_name": data.get("client_name") or "OAuth Client",
        "redirect_uris": redirect_uris,
        "grant_types": grant_types,
        "response_types": response_types,
        "token_endpoint_auth_method": "none",
        "scope": " ".join(scope),
        "client_id_issued_at": timestamp(now_dt),
        "created_at": now,
        "updated_at": now,
    }


def scopes_registered_for_client(client, scopes):
    allowed = normalize_list(client.get("scope")) or [OAUTH_DEFAULT_SCOPE]
    return set(scopes).issubset(set(allowed))


def redirect_with_params(uri, params):
    sep = "&" if "?" in uri else "?"
    return f"{uri}{sep}{urlencode({k: v for k, v in params.items() if v is not None})}"

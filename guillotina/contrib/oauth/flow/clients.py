from urllib.parse import urlencode, urlparse
from uuid import uuid4

from guillotina.contrib.oauth.api.request import normalize_list, oauth_error
from guillotina.contrib.oauth.flow.tokens import utcnow


SUPPORTED_GRANT_TYPES = {"authorization_code", "refresh_token"}
SUPPORTED_RESPONSE_TYPES = {"code"}


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
    if parsed.scheme == "http":
        return parsed.hostname in {"localhost", "127.0.0.1", "::1"} and parsed.path.startswith("/")
    if parsed.scheme.isalpha() and parsed.netloc and parsed.path.startswith("/"):
        return True
    return False


def is_native_redirect_uri(uri):
    parsed = urlparse(uri)
    return parsed.scheme not in ("http", "https")


def redirect_uri_registered_for_client(client, redirect_uri):
    """Return True only if redirect_uri was registered for this client (no side effects).

    Native redirects must be included in the client's dynamic registration request.
    """
    redirect_uris = client.get("redirect_uris") or []
    return redirect_uri in redirect_uris


def make_client(data):
    if data.get("client_id"):
        oauth_error("invalid_request", "client_id is server-issued")
    redirect_uris = data.get("redirect_uris") or []
    if not redirect_uris or not isinstance(redirect_uris, list):
        oauth_error("invalid_request", "redirect_uris is required")
    if any(not validate_redirect_uri(uri) for uri in redirect_uris):
        oauth_error("invalid_request", "unsafe redirect_uri")
    method = data.get("token_endpoint_auth_method", "none")
    if method != "none":
        oauth_error("unsupported_token_endpoint_auth_method")
    grant_types = data.get("grant_types") or ["authorization_code", "refresh_token"]
    response_types = data.get("response_types") or ["code"]
    if not isinstance(grant_types, list) or not grant_types:
        oauth_error("invalid_client_metadata", "grant_types must be a non-empty array")
    if not isinstance(response_types, list) or not response_types:
        oauth_error("invalid_client_metadata", "response_types must be a non-empty array")
    if any(grant_type not in SUPPORTED_GRANT_TYPES for grant_type in grant_types):
        oauth_error("invalid_client_metadata", "unsupported grant_type")
    if any(response_type not in SUPPORTED_RESPONSE_TYPES for response_type in response_types):
        oauth_error("invalid_client_metadata", "unsupported response_type")
    now = utcnow().isoformat()
    return {
        "client_id": uuid4().hex,
        "client_name": data.get("client_name") or "OAuth Client",
        "redirect_uris": redirect_uris,
        "grant_types": grant_types,
        "response_types": response_types,
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

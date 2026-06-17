from urllib.parse import urlparse

from guillotina import app_settings
from guillotina.interfaces import IContainer
from guillotina.utils import get_current_container, get_full_content_path, get_url
from guillotina.utils.misc import build_url


def container_issuer_url(request, container):
    issuer = app_settings.get("oauth", {}).get("issuer")
    if issuer:
        return validate_issuer(issuer)
    if not IContainer.providedBy(container):
        try:
            container = get_current_container()
        except (ValueError, AttributeError, RuntimeError, LookupError):
            pass
    if not IContainer.providedBy(container):
        raise RuntimeError("OAuth container URL requires a container context")
    path = get_full_content_path(container)
    if app_settings.get("oauth", {}).get("trust_proxy_headers", False):
        return get_url(request, path).rstrip("/")
    return build_url(scheme=request.scheme, host=request.host, path=path, query="").rstrip("/")


def validate_issuer(issuer):
    issuer = str(issuer).rstrip("/")
    parsed = urlparse(issuer)
    if parsed.scheme not in ("https", "http") or not parsed.netloc:
        raise RuntimeError("oauth.issuer must be an absolute HTTP(S) URL")
    if parsed.query or parsed.fragment:
        raise RuntimeError("oauth.issuer must not include query or fragment components")
    if parsed.username or parsed.password:
        raise RuntimeError("oauth.issuer must not include userinfo")
    if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("oauth.issuer must use https except for localhost development")
    return issuer

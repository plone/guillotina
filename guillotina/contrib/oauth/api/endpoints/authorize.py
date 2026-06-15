from guillotina import app_settings
from guillotina.auth import authenticate_user
from guillotina.auth.users import AnonymousUser
from guillotina.contrib.oauth.api.endpoints.common import AUTHORIZATION_REQUEST_SINGLETON_PARAMS
from guillotina.contrib.oauth.api.pages import consent_form, login_form, oauth_error_page
from guillotina.contrib.oauth.auth.helpers import authenticate_user_credentials
from guillotina.contrib.oauth.flow.clients import (
    redirect_uri_registered_for_client,
    redirect_with_params,
    scopes_registered_for_client,
)
from guillotina.contrib.oauth.flow.consent import build_consent_key
from guillotina.contrib.oauth.flow.csrf import OAUTH_CSRF_FIELD, csrf_valid
from guillotina.contrib.oauth.flow.pkce import pkce_challenge_valid
from guillotina.contrib.oauth.flow.resources import validate_resource
from guillotina.contrib.oauth.flow.scopes import OAUTH_DEFAULT_SCOPE, oauth_scopes_supported
from guillotina.contrib.oauth.flow.tokens import generate_opaque_token
from guillotina.contrib.oauth.utils.ratelimit import rate_limit_check, rate_limit_exceeded
from guillotina.contrib.oauth.utils.request import (
    normalize_list,
    params_preserving_repeated,
    parse_form_encoded,
    peer_ip_address,
    reject_duplicate_params,
)
from guillotina.contrib.oauth.utils.urls import container_issuer_url
from guillotina.response import HTTPBadRequest, HTTPFound
from guillotina.utils import get_authenticated_user


async def authorization_endpoint(service, store):
    params, error = await _collect_authorization_params(service)
    if error is not None:
        return error
    service.request.oauth_request_params = params

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

    # Mix-up defense (RFC 9207): include the issuer identifier in every
    # authorization response so the client can verify which AS responded.
    issuer = container_issuer_url(service.request, service.context)

    authorization_error = _validate_authorization_request(params, client)
    if authorization_error is not None:
        return _authorization_redirect(redirect_uri, params, issuer, {"error": authorization_error})

    try:
        resources = validate_resource(service.request, service.context, params.get("resource"))
    except HTTPBadRequest:
        return _authorization_redirect(redirect_uri, params, issuer, {"error": "invalid_target"})

    scopes = normalize_list(params.get("scope"))

    auth_result = await _authenticate_user_or_present_login(service, params, client)
    if auth_result.early_response is not None:
        return auth_result.early_response

    response_obj = await _grant_or_request_consent(
        service,
        store,
        params=params,
        client=client,
        user=auth_result.user,
        scopes=scopes,
        resources=resources,
        redirect_uri=redirect_uri,
        issuer=issuer,
        authenticated_now=auth_result.authenticated_now,
    )

    if auth_result.session_token is not None:
        _set_session_cookie(response_obj, auth_result.session_token, service.request)
    return response_obj


async def _collect_authorization_params(service):
    """Merge query and (for POST) body params; returns ``(params, error)``."""
    params = params_preserving_repeated(service.request.query)
    try:
        reject_duplicate_params(service.request.query, AUTHORIZATION_REQUEST_SINGLETON_PARAMS)
    except HTTPBadRequest as exc:
        return None, exc
    if service.request.method == "POST":
        content_type = service.request.headers.get("content-type", "")
        if "application/json" in content_type:
            data = await service.request.json()
        else:
            try:
                data = parse_form_encoded(
                    await service.request.text(), singleton_fields=AUTHORIZATION_REQUEST_SINGLETON_PARAMS
                )
            except HTTPBadRequest as exc:
                return None, exc
        params.update(data)
    return params, None


def _validate_authorization_request(params, client):
    """Validate response_type, PKCE and scope. Returns an OAuth error code or None."""
    if params.get("response_type") != "code":
        return "unsupported_response_type"
    if "code" not in set(client.get("response_types") or []):
        return "unauthorized_client"

    allowed_methods = app_settings.get("oauth", {}).get("allowed_code_challenge_methods", ["S256"])
    code_challenge = params.get("code_challenge")
    if not code_challenge:
        return "invalid_request"
    if not pkce_challenge_valid(code_challenge):
        return "invalid_request"
    if params.get("code_challenge_method") not in allowed_methods:
        return "invalid_request"

    scopes = normalize_list(params.get("scope"))
    supported_scopes = set(oauth_scopes_supported())
    if (
        not scopes
        or OAUTH_DEFAULT_SCOPE not in scopes
        or not set(scopes).issubset(supported_scopes)
        or not scopes_registered_for_client(client, scopes)
    ):
        return "invalid_scope"
    return None


class _AuthenticationResult:
    __slots__ = ("user", "session_token", "authenticated_now", "early_response")

    def __init__(self, *, user=None, session_token=None, authenticated_now=False, early_response=None):
        self.user = user
        self.session_token = session_token
        self.authenticated_now = authenticated_now
        self.early_response = early_response


async def _authenticate_user_or_present_login(service, params, client):
    """Resolve the end user, logging in via the form if needed."""
    user = get_authenticated_user()
    if not isinstance(user, AnonymousUser):
        return _AuthenticationResult(user=user)

    if not (service.request.method == "POST" and params.get("username")):
        return _AuthenticationResult(early_response=login_form(params, client))

    oauth_settings = app_settings.get("oauth", {})
    login_limit = oauth_settings.get("login_rate_limit", 10)
    login_window = oauth_settings.get("login_rate_window", 300)
    login_key = f"oauth-login:{peer_ip_address(service.request)}:{params.get('username')}"

    if await rate_limit_check(login_key, limit=login_limit, window=login_window):
        return _AuthenticationResult(
            early_response=oauth_error_page(
                "Too many attempts",
                "Too many failed login attempts. Please wait and try again.",
                status=429,
            )
        )

    user = await authenticate_user_credentials(params.get("username"), params.get("password", ""))
    if user is None:
        await rate_limit_exceeded(login_key, limit=login_limit, window=login_window)
        return _AuthenticationResult(
            early_response=oauth_error_page(
                "Login failed",
                "The username or password could not be verified.",
                status=401,
            )
        )

    session_token, _ = authenticate_user(user.id)
    return _AuthenticationResult(user=user, session_token=session_token, authenticated_now=True)


def _authorization_redirect(redirect_uri, params, issuer, extra):
    """Build an authorization response redirect (RFC 9207 ``iss`` included)."""
    payload = {"state": params.get("state"), "iss": issuer}
    payload.update(extra)
    return HTTPFound(redirect_with_params(redirect_uri, payload))


async def _grant_or_request_consent(
    service,
    store,
    *,
    params,
    client,
    user,
    scopes,
    resources,
    redirect_uri,
    issuer,
    authenticated_now,
):
    """Handle the consent decision and, when granted, issue the authorization code."""
    consent_key = build_consent_key(user.id, client["client_id"], scopes, resources)
    existing_consent = await store.has_consent(consent_key)

    # A freshly logged-in request never carries a consent decision: the user
    # only submitted credentials, so always render the consent screen next.
    decision = params.get("decision") if service.request.method == "POST" and not authenticated_now else None

    if decision in ("allow", "deny") and not csrf_valid(
        params.get(OAUTH_CSRF_FIELD), params, user.id, scopes, resources
    ):
        return _authorization_redirect(redirect_uri, params, issuer, {"error": "invalid_request"})

    if not existing_consent and decision != "allow":
        if decision == "deny":
            return _authorization_redirect(redirect_uri, params, issuer, {"error": "access_denied"})
        return consent_form(params, client, scopes, resources, user)

    if not existing_consent:
        await store.create_consent(
            consent_key,
            user_id=user.id,
            client_id=client["client_id"],
            scope=scopes,
            resource=resources,
        )

    raw_code = generate_opaque_token("goc_")
    await store.create_code(
        raw_code=raw_code,
        client_id=client["client_id"],
        user_id=user.id,
        redirect_uri=redirect_uri,
        scope=scopes,
        resource=resources,
        code_challenge=params.get("code_challenge"),
    )
    return _authorization_redirect(redirect_uri, params, issuer, {"code": raw_code})


def _set_session_cookie(response, session_token, request):
    secure = ""
    if str(getattr(request, "scheme", "") or "").lower() == "https":
        secure = "; Secure"
    response.headers["Set-Cookie"] = f"auth_token={session_token}; Path=/; HttpOnly; SameSite=Lax{secure}"

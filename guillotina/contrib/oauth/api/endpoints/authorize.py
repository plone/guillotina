from guillotina import app_settings
from guillotina.contrib.oauth.api.endpoints.common import AUTHORIZE_SINGLETON_PARAMS, authenticate_basic
from guillotina.contrib.oauth.api.request import (
    client_identifier,
    normalize_list,
    params_preserving_repeated,
    parse_form_encoded,
    reject_duplicate_params,
)
from guillotina.contrib.oauth.api.urls import container_url, validate_resource
from guillotina.contrib.oauth.api.views import consent_form, login_form, oauth_error_page
from guillotina.contrib.oauth.flow.clients import (
    consent_key,
    redirect_uri_registered_for_client,
    redirect_with_params,
    scopes_registered_for_client,
)
from guillotina.contrib.oauth.flow.csrf import OAUTH_CSRF_FIELD, csrf_valid
from guillotina.contrib.oauth.flow.pkce import pkce_challenge_valid
from guillotina.contrib.oauth.flow.ratelimit import rate_limit_check, rate_limit_exceeded
from guillotina.contrib.oauth.flow.scopes import OAUTH_DEFAULT_SCOPE, oauth_scopes_supported
from guillotina.contrib.oauth.flow.tokens import opaque_token
from guillotina.response import HTTPBadRequest, HTTPFound
from guillotina.utils import get_authenticated_user


async def authorize(service, store):
    params, error = await _collect_params(service)
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
    issuer = container_url(service.request, service.context)

    def authz_redirect(extra):
        payload = {"state": params.get("state"), "iss": issuer}
        payload.update(extra)
        return HTTPFound(redirect_with_params(redirect_uri, payload))

    request_error = _validate_request(params, client)
    if request_error is not None:
        return authz_redirect({"error": request_error})
    try:
        resources = validate_resource(service.request, service.context, params.get("resource"))
    except HTTPBadRequest:
        return authz_redirect({"error": "invalid_target"})
    scopes = normalize_list(params.get("scope"))

    user, new_token, authenticated_now, early_response = await _ensure_authenticated(service, params, client)
    if early_response is not None:
        return early_response

    response_obj = await _issue_or_consent(
        service,
        store,
        params=params,
        client=client,
        user=user,
        scopes=scopes,
        resources=resources,
        redirect_uri=redirect_uri,
        authz_redirect=authz_redirect,
        authenticated_now=authenticated_now,
    )

    if new_token is not None:
        secure = ""
        if str(getattr(service.request, "scheme", "") or "").lower() == "https":
            secure = "; Secure"
        response_obj.headers["Set-Cookie"] = f"auth_token={new_token}; Path=/; HttpOnly; SameSite=Lax{secure}"
    return response_obj


async def _collect_params(service):
    """Merge query and (for POST) body params; returns ``(params, error)``."""
    params = params_preserving_repeated(service.request.query)
    try:
        reject_duplicate_params(service.request.query, AUTHORIZE_SINGLETON_PARAMS)
    except HTTPBadRequest as exc:
        return None, exc
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
                return None, exc
        params.update(data)
    return params, None


def _validate_request(params, client):
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


async def _ensure_authenticated(service, params, client):
    """Resolve the end user, logging in via the form if needed.

    Returns ``(user, new_token, authenticated_now, early_response)``. When
    ``early_response`` is not None the caller must return it immediately (login
    form, rate-limit page or failed-login page).
    """
    user = get_authenticated_user()
    if user is not None and getattr(user, "id", "Anonymous User") != "Anonymous User":
        return user, None, False, None
    if not (service.request.method == "POST" and params.get("username")):
        return None, None, False, login_form(params, client)

    oauth_settings = app_settings.get("oauth", {})
    login_limit = oauth_settings.get("login_rate_limit", 10)
    login_window = oauth_settings.get("login_rate_window", 300)
    login_key = f"oauth-login:{client_identifier(service.request)}:{params.get('username')}"
    if await rate_limit_check(login_key, limit=login_limit, window=login_window):
        return (
            None,
            None,
            False,
            oauth_error_page(
                "Too many attempts",
                "Too many failed login attempts. Please wait and try again.",
                status=429,
            ),
        )
    user = await authenticate_basic(params.get("username"), params.get("password", ""))
    if user is None:
        await rate_limit_exceeded(login_key, limit=login_limit, window=login_window)
        return (
            None,
            None,
            False,
            oauth_error_page(
                "Login failed",
                "The username or password could not be verified.",
                status=401,
            ),
        )
    from guillotina.auth import authenticate_user

    new_token, _ = authenticate_user(user.id)
    return user, new_token, True, None


async def _issue_or_consent(
    service,
    store,
    *,
    params,
    client,
    user,
    scopes,
    resources,
    redirect_uri,
    authz_redirect,
    authenticated_now,
):
    """Handle the consent decision and, when granted, issue the auth code."""
    ckey = consent_key(user.id, client["client_id"], scopes, resources)
    existing_consent = await store.has_consent(ckey)
    # A freshly logged-in request never carries a consent decision: the user
    # only submitted credentials, so always render the consent screen next.
    decision = params.get("decision") if service.request.method == "POST" and not authenticated_now else None
    if decision in ("allow", "deny") and not csrf_valid(
        params.get(OAUTH_CSRF_FIELD), params, user.id, scopes, resources
    ):
        return authz_redirect({"error": "invalid_request"})
    if not existing_consent and decision != "allow":
        if decision == "deny":
            return authz_redirect({"error": "access_denied"})
        return consent_form(params, client, scopes, resources, user)

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
    return authz_redirect({"code": raw_code})

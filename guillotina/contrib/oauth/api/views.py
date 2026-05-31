from base64 import b64encode
from functools import lru_cache
from html import escape as html_escape
from pathlib import Path
from string import Template

from guillotina.contrib.oauth.flow.csrf import OAUTH_CSRF_FIELD, csrf_token
from guillotina.contrib.oauth.flow.scopes import OAUTH_SCOPE_DESCRIPTIONS
from guillotina.response import Response


TEMPLATE_DIR = Path(__file__).parent / "templates"
BRAND_LOGO_PATH = Path(__file__).parents[3] / "static" / "assets" / "brand" / "guillotina-logo-horizontal.svg"


def _html(body, status=200):
    return Response(
        body=body.encode("utf-8"),
        status=status,
        content_type="text/html",
        headers={
            "Content-Security-Policy": "frame-ancestors 'none'",
            "X-Frame-Options": "DENY",
        },
    )


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
        OAUTH_CSRF_FIELD,
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


def oauth_error_page(title, message, *, status):
    return _oauth_page(
        title,
        title,
        _render_template("error.html", message=html_escape(message)),
        status=status,
        tone="error",
    )


def login_form(params, client):
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


def consent_form(params, client, scopes, resources, user):
    raw_client_name = client.get("client_name") or client["client_id"]
    client_name = html_escape(raw_client_name)
    consent_params = dict(params)
    consent_params[OAUTH_CSRF_FIELD] = csrf_token(consent_params, user.id, scopes, resources)
    body = _render_template(
        "consent.html",
        client_name=client_name,
        user_id=html_escape(str(user.id)),
        client_id=html_escape(client["client_id"]),
        redirect_uri=html_escape(consent_params.get("redirect_uri", "")),
        scope_items=_scope_items(scopes),
        resource_items=_list_items(resources, empty="Default Guillotina container"),
        hidden_inputs=_hidden_inputs(consent_params),
    )
    return _oauth_page("Authorize OAuth Client", f"Allow {raw_client_name}?", body)

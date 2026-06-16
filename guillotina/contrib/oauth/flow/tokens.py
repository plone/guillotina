import secrets
from datetime import datetime, timedelta, timezone

import jwt

from guillotina import app_settings
from guillotina.contrib.oauth.utils.crypto import access_token_signing_key


def generate_opaque_token(prefix=""):
    value = secrets.token_urlsafe(48)
    return f"{prefix}{value}" if prefix else value


def issue_access_token(*, issuer, subject, audience, client_id, scope):
    now = datetime.now(timezone.utc)
    ttl = app_settings["oauth"].get("access_token_ttl", 3600)
    claims = {
        "iss": issuer,
        "sub": subject,
        "id": subject,
        "aud": list(audience),
        "client_id": client_id,
        "scope": " ".join(scope),
        "iat": now,
        "exp": now + timedelta(seconds=ttl),
        "token_type": "oauth_access_token",
    }
    token = jwt.encode(claims, access_token_signing_key(), algorithm=app_settings["jwt"]["algorithm"])
    return token, claims

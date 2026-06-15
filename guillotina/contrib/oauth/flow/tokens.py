import secrets
from datetime import timedelta

import jwt

from guillotina import app_settings
from guillotina.contrib.oauth.utils.crypto import access_token_signing_key
from guillotina.contrib.oauth.utils.time import timestamp, utcnow


def generate_opaque_token(prefix=""):
    value = secrets.token_urlsafe(48)
    return f"{prefix}{value}" if prefix else value


def issue_access_token(*, issuer, subject, audience, client_id, scope):
    now = utcnow()
    ttl = app_settings["oauth"].get("access_token_ttl", 3600)
    claims = {
        "iss": issuer,
        "sub": subject,
        "id": subject,
        "aud": list(audience),
        "client_id": client_id,
        "scope": " ".join(scope),
        "iat": timestamp(now),
        "exp": timestamp(now + timedelta(seconds=ttl)),
        "token_type": "oauth_access_token",
    }
    token = jwt.encode(claims, access_token_signing_key(), algorithm=app_settings["jwt"]["algorithm"])
    return token, claims

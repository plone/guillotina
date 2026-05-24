import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

import jwt

from guillotina import app_settings


def utcnow():
    return datetime.utcnow()


def timestamp(dt):
    return int(dt.timestamp())


def opaque_token(prefix=""):
    value = secrets.token_urlsafe(48)
    return f"{prefix}{value}" if prefix else value


def token_hash(token: str) -> str:
    secret = app_settings.get("jwt", {}).get("secret", "") or "guillotina-oauth-dev-secret"
    return hmac.new(secret.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()


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
    token = jwt.encode(claims, app_settings["jwt"]["secret"], algorithm=app_settings["jwt"]["algorithm"])
    return token, claims

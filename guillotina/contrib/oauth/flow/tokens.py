import calendar
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

import jwt

from guillotina import app_settings
from guillotina.contrib.oauth.flow.keys import derive_key


def utcnow():
    return datetime.utcnow()


def timestamp(dt):
    return int(calendar.timegm(dt.utctimetuple()))


def opaque_token(prefix=""):
    value = secrets.token_urlsafe(48)
    return f"{prefix}{value}" if prefix else value


def token_hash(token: str) -> str:
    key = derive_key("token-hash")
    return hmac.new(key, token.encode("utf-8"), hashlib.sha256).hexdigest()


def access_token_key() -> bytes:
    return derive_key("access-token")


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
    token = jwt.encode(claims, access_token_key(), algorithm=app_settings["jwt"]["algorithm"])
    return token, claims

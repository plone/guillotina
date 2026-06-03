import hashlib
import hmac
import json
import time
from base64 import b64decode, b64encode
from binascii import Error as BinasciiError

from guillotina import app_settings
from guillotina.contrib.oauth.flow.keys import derive_key


OAUTH_CSRF_FIELD = "oauth_csrf"


def _csrf_base_payload(params, user_id, scopes, resources):
    return {
        "user_id": str(user_id),
        "client_id": str(params.get("client_id") or ""),
        "redirect_uri": str(params.get("redirect_uri") or ""),
        "response_type": str(params.get("response_type") or ""),
        "scope": list(scopes),
        "state": str(params.get("state") or ""),
        "code_challenge": str(params.get("code_challenge") or ""),
        "code_challenge_method": str(params.get("code_challenge_method") or ""),
        "resource": list(resources),
    }


def _b64url_encode(raw):
    return b64encode(raw).rstrip(b"=").decode("ascii").replace("+", "-").replace("/", "_")


def _b64url_decode(value):
    padded = value.replace("-", "+").replace("_", "/")
    padded += "=" * (-len(padded) % 4)
    return b64decode(padded.encode("ascii"))


def _csrf_signature(body):
    secret = derive_key("csrf")
    return _b64url_encode(hmac.new(secret, body.encode("ascii"), hashlib.sha256).digest())


def csrf_token(params, user_id, scopes, resources):
    payload = _csrf_base_payload(params, user_id, scopes, resources)
    payload["iat"] = int(time.time())
    body = _b64url_encode(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return f"{body}.{_csrf_signature(body)}"


def csrf_valid(token, params, user_id, scopes, resources):
    if not token or not isinstance(token, str) or "." not in token:
        return False
    body, _, signature = token.partition(".")
    try:
        if not hmac.compare_digest(_csrf_signature(body), signature):
            return False
        payload = json.loads(_b64url_decode(body).decode("utf-8"))
    except (BinasciiError, UnicodeDecodeError, UnicodeEncodeError, ValueError, TypeError):
        return False
    issued_at = payload.get("iat")
    if not isinstance(issued_at, int):
        return False
    ttl = app_settings.get("oauth", {}).get("authorize_csrf_ttl", 600)
    now = int(time.time())
    if issued_at > now + 60 or now - issued_at > ttl:
        return False
    expected = _csrf_base_payload(params, user_id, scopes, resources)
    return all(payload.get(key) == value for key, value in expected.items())

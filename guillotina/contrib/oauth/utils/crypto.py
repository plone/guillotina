import hashlib
import hmac

from guillotina.contrib.oauth.flow.keys import derive_key


def token_hash(token: str) -> str:
    key = derive_key("token-hash")
    return hmac.new(key, token.encode("utf-8"), hashlib.sha256).hexdigest()


def access_token_signing_key() -> bytes:
    return derive_key("access-token")

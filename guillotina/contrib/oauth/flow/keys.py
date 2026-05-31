"""Purpose-specific key derivation for OAuth secrets.

All OAuth HMAC operations are keyed from the single configured ``jwt.secret``.
To avoid using the same raw key for unrelated purposes (token hashing, CSRF
signing, ...), every consumer derives a distinct subkey bound to a stable
purpose label. This provides cryptographic domain separation: compromising or
analysing one usage does not weaken the others.

Access-token JWTs, token hashes and CSRF signatures each use a separate derived
key so an OAuth token cannot be validated by Guillotina's generic JWT validator.
"""

import hashlib
import hmac

from guillotina import app_settings


def _base_secret() -> bytes:
    secret = app_settings.get("jwt", {}).get("secret")
    if not secret:
        raise RuntimeError(
            "OAuth key derivation requires `jwt.secret` to be configured; "
            "refusing to fall back to an insecure default secret."
        )
    return secret.encode("utf-8")


def derive_key(purpose: str) -> bytes:
    """Return a 32-byte key bound to ``purpose``, derived from ``jwt.secret``."""
    return hmac.new(_base_secret(), f"guillotina.oauth:{purpose}".encode("utf-8"), hashlib.sha256).digest()

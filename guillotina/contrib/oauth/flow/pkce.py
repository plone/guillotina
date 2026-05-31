import base64
import hashlib
import re
from typing import Optional


_VERIFIER_CHARS = re.compile(r"^[A-Za-z0-9\-._~]{43,128}$")
_CHALLENGE_CHARS = re.compile(r"^[A-Za-z0-9\-._~]{43,128}$")


def pkce_verifier_valid(verifier: Optional[str]) -> bool:
    """Return True when ``code_verifier`` conforms to RFC 7636."""

    if not verifier or not isinstance(verifier, str):
        return False
    return _VERIFIER_CHARS.fullmatch(verifier) is not None


def pkce_challenge_valid(challenge: Optional[str]) -> bool:
    """Return True when ``code_challenge`` conforms to RFC 7636 syntax."""

    if not challenge or not isinstance(challenge, str):
        return False
    return _CHALLENGE_CHARS.fullmatch(challenge) is not None


def s256_challenge_from_bytes(verifier: bytes) -> str:
    digest = hashlib.sha256(verifier).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def s256_challenge(verifier: str) -> str:
    return s256_challenge_from_bytes(verifier.encode("ascii"))


def verify_s256(verifier: str, challenge: str) -> bool:
    if not pkce_verifier_valid(verifier):
        return False
    return s256_challenge(verifier) == challenge

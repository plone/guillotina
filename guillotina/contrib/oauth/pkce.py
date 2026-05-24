import base64
import hashlib


def s256_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def verify_s256(verifier: str, challenge: str) -> bool:
    return s256_challenge(verifier) == challenge

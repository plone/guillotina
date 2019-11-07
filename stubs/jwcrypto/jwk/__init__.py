from typing import Dict


class JWK:
    def generate(self, kty: str, size: int = 256) -> Dict[str, str]:
        ...

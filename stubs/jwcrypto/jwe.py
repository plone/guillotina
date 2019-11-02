from typing import Any
from typing import Dict


class JWE:
    def __init__(self, payload: bytes, key: bytes):
        ...

    def add_recipient(self, key: Dict[str, Any]):
        ...

    def serialize(self, compact: bool) -> str:
        ...

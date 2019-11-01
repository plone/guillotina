from typing import Any


class LRU:
    def __init__(self, size: int):
        ...

    def set(self, key: str, value: Any) -> None:
        ...

    def get(self, key: str) -> Any:
        ...

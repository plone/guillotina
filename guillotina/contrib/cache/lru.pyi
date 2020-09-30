from typing import Any, Callable
from typing import Dict
from typing import Optional


class LRU(Dict[str, Any]):
    def __init__(self, size: int, callback: Callable[[str, Any], Any]):
        ...

    def set(self, key: str, value: Any, size: Optional[int] = None) -> None:
        ...

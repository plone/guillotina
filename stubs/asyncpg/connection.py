from .types import Record
from typing import List


class Connection:
    async def _do_execute(self, query, *args, **kwargs) -> List[Record]:
        ...

    async def fetch(self, sql: str) -> List[Record]:
        ...

    async def close(self):
        ...

    async def execute(self, sql: str):
        ...


class ServerCapabilities:
    ...

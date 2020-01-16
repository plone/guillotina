from typing import AsyncIterator


class Channel:
    async def wait_message(self) -> AsyncIterator[bool]:
        ...

    async def get(self) -> bytes:
        ...


class Redis:
    def __init__(self, conn):
        ...

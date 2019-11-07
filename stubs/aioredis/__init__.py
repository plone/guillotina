from typing import AsyncIterator


class Channel:
    async def wait_message(self) -> AsyncIterator[bool]:
        ...

    async def get(self) -> bytes:
        ...

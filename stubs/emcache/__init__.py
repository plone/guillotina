from typing import Optional
from typing import List


class Item:
    value: bytes


class MemcachedHostAddress:
    address: str
    port: int

    def __init__(self, address: str, port: int) -> None:
        pass


class Node:
    pass


class Client:
    async def get(self, key: bytes) -> Item:
        pass

    async def set(self, key: bytes, value: bytes, exptime: Optional[int] = None):
        pass

    async def delete(self, key: bytes):
        pass

    async def flush_all(self, node: Node) -> None:
        pass

    def cluster_managment(self):
        pass


async def create_client(servers: List[MemcachedHostAddress], timeout: int, max_connections: int, purge_unused_connections_after: int, connection_timeout: int, purge_unhealthy_nodes: bool) -> Client:
    pass

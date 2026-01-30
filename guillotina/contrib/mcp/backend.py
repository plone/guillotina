from contextvars import ContextVar
from guillotina.component import get_multi_adapter
from guillotina.component import query_utility
from guillotina.interfaces import ICatalogUtility
from guillotina.interfaces import IResource
from guillotina.interfaces import IResourceSerializeToJson
from guillotina.utils import get_object_by_uid
from guillotina.utils import navigate_to
from zope.interface import Interface

import typing


class IMCPBackend(Interface):
    async def search(context: IResource, query: dict) -> dict:
        pass

    async def count(context: IResource, query: dict) -> int:
        pass

    async def get_content(context: IResource, path: typing.Optional[str], uid: typing.Optional[str]) -> dict:
        pass

    async def list_children(
        context: IResource,
        path: str,
        _from: int = 0,
        _size: int = 20,
    ) -> dict:
        pass


_mcp_context_var: ContextVar[typing.Optional[IResource]] = ContextVar("mcp_context", default=None)


def get_mcp_context():
    return _mcp_context_var.get()


def set_mcp_context(context: IResource):
    _mcp_context_var.set(context)


def clear_mcp_context():
    try:
        _mcp_context_var.set(None)
    except LookupError:
        pass


class InProcessBackend:
    def _get_base_context(self) -> IResource:
        ctx = get_mcp_context()
        if ctx is None:
            raise RuntimeError("MCP context not set (not in @mcp request?)")
        return ctx

    async def search(self, context: IResource, query: dict) -> dict:
        base = context if context is not None else self._get_base_context()
        search = query_utility(ICatalogUtility)
        if search is None:
            return {"items": [], "items_total": 0}
        return await search.search(base, query)

    async def count(self, context: IResource, query: dict) -> int:
        base = context if context is not None else self._get_base_context()
        search = query_utility(ICatalogUtility)
        if search is None:
            return 0
        return await search.count(base, query)

    async def get_content(
        self,
        context: IResource,
        path: typing.Optional[str],
        uid: typing.Optional[str],
    ) -> dict:
        from guillotina import task_vars

        base = context if context is not None else self._get_base_context()
        request = task_vars.request.get()
        if uid:
            try:
                ob = await get_object_by_uid(uid)
            except KeyError:
                return {}
            if not self._in_container_tree(ob, base):
                return {}
        elif path is not None:
            rel_path = path.strip("/") or ""
            try:
                ob = await navigate_to(base, "/" + rel_path) if rel_path else base
            except KeyError:
                return {}
        else:
            return {}
        serializer = get_multi_adapter((ob, request), IResourceSerializeToJson)
        return await serializer()

    def _in_container_tree(self, ob: IResource, container: IResource) -> bool:
        from guillotina.utils import get_content_path

        ob_path = get_content_path(ob)
        cont_path = get_content_path(container)
        return ob_path == cont_path or ob_path.startswith(cont_path.rstrip("/") + "/")

    async def list_children(
        self,
        context: IResource,
        path: str,
        _from: int = 0,
        _size: int = 20,
    ) -> dict:
        base = context if context is not None else self._get_base_context()
        path = path.strip("/") or ""
        try:
            container = await navigate_to(base, "/" + path) if path else base
        except KeyError:
            return {"items": [], "items_total": 0}
        from guillotina import task_vars
        from guillotina.interfaces import IFolder
        from guillotina.interfaces import IResourceSerializeToJsonSummary

        if not IFolder.providedBy(container):
            return {"items": [], "items_total": 0}
        request = task_vars.request.get()
        items = []
        total = 0
        async for name, child in container.async_items():
            if total >= _from + _size:
                total += 1
                continue
            if total >= _from:
                summary_serializer = get_multi_adapter((child, request), IResourceSerializeToJsonSummary)
                items.append(await summary_serializer())
            total += 1
        return {"items": items, "items_total": total}


def _encode_basic_auth(username: str, password: str) -> str:
    import base64

    credentials = f"{username}:{password or ''}"
    return base64.b64encode(credentials.encode()).decode()


class HttpBackend:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password or ""
        self._auth_header = f"Basic {_encode_basic_auth(username, password)}"

    def _url(self, path: str, query: typing.Optional[dict] = None) -> str:
        path = path.strip("/")
        url = f"{self.base_url}/{path}"
        if query:
            from urllib.parse import urlencode

            url += "?" + urlencode(query)
        return url

    async def search(self, context: IResource, query: dict) -> dict:
        import httpx

        path = context if isinstance(context, str) else None
        if not path:
            return {"items": [], "items_total": 0}
        url = self._url(f"{path}/@search", query)
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers={"Authorization": self._auth_header}, timeout=30.0)
            resp.raise_for_status()
            return resp.json()

    async def count(self, context: IResource, query: dict) -> int:
        import httpx

        path = context if isinstance(context, str) else None
        if not path:
            return 0
        url = self._url(f"{path}/@count", query)
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers={"Authorization": self._auth_header}, timeout=30.0)
            resp.raise_for_status()
            return resp.json()

    async def get_content(
        self,
        context: IResource,
        path: typing.Optional[str],
        uid: typing.Optional[str],
    ) -> dict:
        import httpx

        base_path = context if isinstance(context, str) else None
        if not base_path:
            return {}
        if uid:
            url = self._url(f"{base_path}/@resolveuid/{uid}")
            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.get(url, headers={"Authorization": self._auth_header}, timeout=30.0)
                if resp.status_code == 404:
                    return {}
                resp.raise_for_status()
                target = resp.headers.get("location") or ""
                if not target.startswith("http"):
                    return {}
                resp2 = await client.get(target, headers={"Authorization": self._auth_header}, timeout=30.0)
                resp2.raise_for_status()
                return resp2.json()
        elif path is not None:
            rel = path.strip("/")
            url_path = f"{base_path}/{rel}" if rel else base_path
            url = self._url(url_path)
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers={"Authorization": self._auth_header}, timeout=30.0)
                if resp.status_code == 404:
                    return {}
                resp.raise_for_status()
                return resp.json()
        return {}

    async def list_children(
        self,
        context: IResource,
        path: str,
        _from: int = 0,
        _size: int = 20,
    ) -> dict:
        import httpx

        base_path = context if isinstance(context, str) else None
        if not base_path:
            return {"items": [], "items_total": 0}
        rel = path.strip("/") if path else ""
        url_path = f"{base_path}/{rel}" if rel else base_path
        page = (_from // _size) + 1 if _size else 1
        query = {"page": str(page), "page_size": str(_size or 20)}
        url = self._url(f"{url_path}/@items", query)
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers={"Authorization": self._auth_header}, timeout=30.0)
            if resp.status_code == 404:
                return {"items": [], "items_total": 0}
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", []) if isinstance(data, dict) else []
            total = data.get("total", len(items)) if isinstance(data, dict) else len(items)
            return {"items": items, "items_total": total}

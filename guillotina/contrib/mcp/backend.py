from contextvars import ContextVar
from guillotina.component import get_multi_adapter
from guillotina.component import query_utility
from guillotina.interfaces import ICatalogUtility
from guillotina.interfaces import IResource
from guillotina.interfaces import IResourceSerializeToJson
from guillotina.utils import get_object_by_uid
from guillotina.utils import get_security_policy
from guillotina.utils import navigate_to

import typing


_mcp_context_var: ContextVar[typing.Optional[IResource]] = ContextVar("mcp_context", default=None)


def get_mcp_context():
    return _mcp_context_var.get()


def set_mcp_context(context: IResource):
    _mcp_context_var.set(context)


def clear_mcp_context():
    try:
        _mcp_context_var.set(None)
    except LookupError:
        pass  # No active context set; clear operation is intentionally idempotent.


class InProcessBackend:
    def _get_base_context(self) -> IResource:
        ctx = get_mcp_context()
        if ctx is None:
            raise RuntimeError("MCP context not set (not in @mcp request?)")
        return ctx

    def _resolve_context(self, context: typing.Optional[IResource]) -> IResource:
        if context is None:
            return self._get_base_context()
        if not IResource.providedBy(context):
            raise RuntimeError(
                "InProcessBackend requires IResource context. Use the @mcp endpoint or set MCP context."
            )
        return context

    async def search(self, context: IResource, query: dict) -> dict:
        base = self._resolve_context(context)
        search = query_utility(ICatalogUtility)
        if search is None:
            return {"items": [], "items_total": 0}
        return await search.search(base, query)

    async def count(self, context: IResource, query: dict) -> int:
        base = self._resolve_context(context)
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

        base = self._resolve_context(context)
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
        if not get_security_policy().check_permission("guillotina.ViewContent", ob):
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
        base = self._resolve_context(context)
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
        if not get_security_policy().check_permission("guillotina.ViewContent", container):
            return {"items": [], "items_total": 0}
        request = task_vars.request.get()
        policy = get_security_policy()
        visible = []
        async for name, child in container.async_items():
            if policy.check_permission("guillotina.ViewContent", child):
                summary_serializer = get_multi_adapter((child, request), IResourceSerializeToJsonSummary)
                visible.append(await summary_serializer())
        items_total = len(visible)
        items = visible[_from : _from + _size]
        return {"items": items, "items_total": items_total}

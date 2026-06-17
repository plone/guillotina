"""Discovery routing — well-known handler registry and request dispatching."""

from guillotina import task_vars
from guillotina.contrib.oauth.storage.access import get_oauth_store
from guillotina.interfaces import IContainer
from guillotina.response import HTTPNotFound
from guillotina.transactions import transaction
from guillotina.utils import get_database, get_registry


WELL_KNOWN_HANDLERS = {}


def register_well_known_handler(name, handler):
    WELL_KNOWN_HANDLERS[name] = handler


def _split_well_known_target_path(path_value, *, allow_resource_path=False):
    parts = [part for part in path_value.strip("/").split("/") if part]
    if len(parts) < 2:
        raise HTTPNotFound(content={"reason": "Invalid path"})
    if not allow_resource_path and len(parts) > 2:
        raise HTTPNotFound(content={"reason": "Invalid issuer path"})
    return parts[0], parts[1], "/" + "/".join(parts)


async def serve_well_known_metadata(request, action, target_path, handlers):
    allow_resource_path = action == "oauth-protected-resource"
    db_id, container_id, protected_resource_path = _split_well_known_target_path(
        target_path, allow_resource_path=allow_resource_path
    )
    db = await get_database(db_id)
    async with transaction(db=db):
        root = await db.get_transaction_manager().get_root()
        try:
            container = await root.async_get(container_id)
        except KeyError:
            raise HTTPNotFound(content={"reason": "Container not found"})
        if not IContainer.providedBy(container):
            raise HTTPNotFound(content={"reason": "Container not found"})
        task_vars.container.set(container)
        task_vars.registry.set(None)
        await get_registry(container)
        get_oauth_store(container, require_installed=True)
        if allow_resource_path:
            request.oauth_protected_resource_path = protected_resource_path
        return handlers[action](request, container)

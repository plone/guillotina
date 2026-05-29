from guillotina import task_vars
from guillotina.contrib.oauth.storage.access import get_oauth_store
from guillotina.interfaces import IContainer
from guillotina.response import HTTPNotFound
from guillotina.transactions import transaction
from guillotina.utils import get_database, get_registry


def _container_path_parts(path_value, *, allow_mcp_suffix=False):
    parts = [part for part in path_value.strip("/").split("/") if part]
    if len(parts) < 2:
        raise HTTPNotFound(content={"reason": "Invalid path"})
    suffix = parts[2:]
    if allow_mcp_suffix:
        if suffix and suffix != ["@mcp", "protocol"]:
            raise HTTPNotFound(content={"reason": "Invalid resource path"})
    elif suffix:
        raise HTTPNotFound(content={"reason": "Invalid issuer path"})
    return parts[0], parts[1]


async def rfc_well_known_response(request, action, target_path, handlers):
    if action == "oauth-protected-resource":
        db_id, container_id = _container_path_parts(target_path, allow_mcp_suffix=True)
    else:
        db_id, container_id = _container_path_parts(target_path)
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
        return handlers[action](request, container)

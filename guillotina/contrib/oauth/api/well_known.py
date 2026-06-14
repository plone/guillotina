from guillotina import task_vars
from guillotina.contrib.oauth.api.urls import container_url
from guillotina.contrib.oauth.flow.scopes import oauth_scopes_supported
from guillotina.contrib.oauth.storage.access import get_oauth_store
from guillotina.interfaces import IContainer
from guillotina.response import HTTPNotFound
from guillotina.transactions import transaction
from guillotina.utils import get_database, get_registry


# Registry of ``.well-known`` metadata handlers keyed by document name. Other
# packages (e.g. the MCP integration) register additional documents here.
WELL_KNOWN_HANDLERS = {}


def register_well_known_handler(name, handler):
    WELL_KNOWN_HANDLERS[name] = handler


def _authorization_server_metadata(request, container):
    issuer = container_url(request, container)
    return {
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/oauth/authorize",
        "token_endpoint": f"{issuer}/oauth/token",
        "registration_endpoint": f"{issuer}/oauth/register",
        "revocation_endpoint": f"{issuer}/oauth/revoke",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "revocation_endpoint_auth_methods_supported": ["none"],
        "resource_indicators_supported": True,
        "authorization_response_iss_parameter_supported": True,
        "scopes_supported": oauth_scopes_supported(),
    }


register_well_known_handler("oauth-authorization-server", _authorization_server_metadata)


def _container_path_parts(path_value, *, allow_mcp_suffix=False):
    parts = [part for part in path_value.strip("/").split("/") if part]
    if len(parts) < 2:
        raise HTTPNotFound(content={"reason": "Invalid path"})
    suffix = parts[2:]
    if allow_mcp_suffix:
        if suffix and suffix[-2:] != ["@mcp", "protocol"]:
            raise HTTPNotFound(content={"reason": "Invalid resource path"})
    elif suffix:
        raise HTTPNotFound(content={"reason": "Invalid issuer path"})
    return parts[0], parts[1], "/" + "/".join(parts)


async def rfc_well_known_response(request, action, target_path, handlers):
    if action == "oauth-protected-resource":
        db_id, container_id, protected_resource_path = _container_path_parts(
            target_path, allow_mcp_suffix=True
        )
    else:
        db_id, container_id, protected_resource_path = _container_path_parts(target_path)
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
        if action == "oauth-protected-resource":
            request.oauth_protected_resource_path = protected_resource_path
        return handlers[action](request, container)

from guillotina import configure
from guillotina.component import query_utility
from guillotina.contrib.mcp.interfaces import IMCPToolRegistry
from guillotina.interfaces import (
    IBeforeObjectRemovedEvent,
    IObjectAddedEvent,
    IObjectModifiedEvent,
    IResource,
)


@configure.subscriber(for_=(IResource, IObjectAddedEvent))
@configure.subscriber(for_=(IResource, IObjectModifiedEvent))
@configure.subscriber(for_=(IResource, IBeforeObjectRemovedEvent))
async def invalidate_mcp_cache_on_content_change(obj, event):
    registry = query_utility(IMCPToolRegistry)
    if registry is None:
        return
    object_id = getattr(obj, "id", None) or getattr(obj, "__name__", None) or "unknown"
    registry.schedule_invalidate_cache(reason=f"{event.__class__.__name__}:{object_id}")

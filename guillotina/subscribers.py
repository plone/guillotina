from datetime import datetime
from dateutil.tz import tzutc
from guillotina.component import query_utility
from guillotina import configure
from guillotina.component._api import get_component_registry
from guillotina.api.container import DefaultPOST as DefaultPOSTContainer
from guillotina.api.content import DefaultPOST as DefaultPOSTContent
from guillotina.api.content import DefaultDELETE

from guillotina.component.interfaces import ComponentLookupError
from guillotina.component.interfaces import IObjectEvent
from guillotina.api.httpcache import IHttpCachePolicyUtility
from guillotina.interfaces import IObjectModifiedEvent
from guillotina.interfaces import IRequestFinishedEvent
from guillotina.interfaces import IResource


_zone = tzutc()


@configure.subscriber(for_=(IResource, IObjectModifiedEvent))
def modified_object(obj, event):
    """Set the modification date of an object."""
    now = datetime.now(tz=_zone)
    obj.modification_date = now


@configure.subscriber(for_=IObjectEvent)
async def object_event_notify(event):
    """Dispatch ObjectEvents to interested adapters."""
    try:
        sitemanager = get_component_registry()
    except ComponentLookupError:
        # Oh blast, no site manager. This should *never* happen!
        return []

    return await sitemanager.adapters.asubscribers((event.object, event), None)


@configure.subscriber(
    for_=IRequestFinishedEvent)
async def add_http_cache_headers(event):
    """This will add, if configured, the corresponding http cache headers
    on the response
    """
    if isinstance(event.view, (DefaultDELETE, DefaultPOSTContainer, DefaultPOSTContent)):
        # Just update headers if not creating content or method request is delete
        return

    # Compute global http cache policy
    extra_headers = {}
    global_policy = query_utility(IHttpCachePolicyUtility)
    if global_policy is not None:
        extra_headers = global_policy(event.resource, event.request)

    # Update with view headers
    aux = getattr(event.view, "__extra_headers__", {})
    if isinstance(aux, dict):
        extra_headers.update(**aux)
    elif callable(aux):
        extra_headers.update(**aux(context=event.resource,
                                   request=event.request))

    if not extra_headers:
        return
    # Add http cache headers on response
    event.response._headers.update(**extra_headers)

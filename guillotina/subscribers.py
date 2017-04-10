from datetime import datetime
from dateutil.tz import tzlocal
from guillotina import configure
from guillotina.component._api import subscribers as component_subscribers
from guillotina.component._api import getSiteManager
from guillotina.component.interfaces import ComponentLookupError
from guillotina.component.interfaces import IObjectEvent
from guillotina.interfaces import IObjectModifiedEvent
from guillotina.interfaces import IResource


_zone = tzlocal()


@configure.subscriber(for_=(IResource, IObjectModifiedEvent))
def modified_object(obj, event):
    """Set the modification date of an object."""
    now = datetime.now(tz=_zone)
    obj.modification_date = now


@configure.subscriber(for_=IObjectEvent)
async def object_event_notify(event):
    """Dispatch ObjectEvents to interested adapters."""
    try:
        sitemanager = getSiteManager()
    except ComponentLookupError:
        # Oh blast, no site manager. This should *never* happen!
        return []

    # sync subscribers
    component_subscribers((event.object, event), None)
    return await sitemanager.adapters.asubscribers((event.object, event), None)

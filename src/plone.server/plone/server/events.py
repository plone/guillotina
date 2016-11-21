from datetime import datetime
from dateutil.tz import tzlocal
from plone.server.interfaces import INewUserAdded
from plone.server.interfaces import IObjectFinallyCreatedEvent
from zope.interface import implementer
from zope.interface.interfaces import ObjectEvent
from zope.event import subscribers as syncsubscribers
from zope.component._api import getSiteManager
from zope.component.interfaces import ComponentLookupError
from zope.component.interfaces import IObjectEvent
from zope.component._declaration import adapter
_zone = tzlocal()

asyncsubscribers = []


@implementer(IObjectFinallyCreatedEvent)
class ObjectFinallyCreatedEvent(ObjectEvent):
    """An object has been created."""


@implementer(INewUserAdded)
class NewUserAdded(object):
    """An object has been created."""

    def __init__(self, user):
        self.user = user


def modified_object(obj, event):
    """Set the modification date of an object."""
    now = datetime.now(tz=_zone)
    obj.modification_date = now


async def notify(event):
    """Notify all subscribers of ``event``."""
    for subscriber in syncsubscribers:
        subscriber(event)
    for subscriber in asyncsubscribers:
        await subscriber(event)

async def dispatch(*event):
    try:
        sitemanager = getSiteManager()
    except ComponentLookupError:
        # Oh blast, no site manager. This should *never* happen!
        return []

    return await sitemanager.adapters.asubscribers(event, None)


@adapter(IObjectEvent)
async def objectEventNotify(event):
    """Dispatch ObjectEvents to interested adapters."""
    try:
        sitemanager = getSiteManager()
    except ComponentLookupError:
        # Oh blast, no site manager. This should *never* happen!
        return []

    return await sitemanager.adapters.asubscribers((event.object, event), None)

asyncsubscribers.append(dispatch)

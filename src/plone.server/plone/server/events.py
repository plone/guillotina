from datetime import datetime
from dateutil.tz import tzlocal
from plone.server import configure
from plone.server.interfaces import IBeforeJSONAssignedEvent
from plone.server.interfaces import IFileFinishUploaded
from plone.server.interfaces import INewUserAdded
from plone.server.interfaces import IObjectFinallyCreatedEvent
from plone.server.interfaces import IObjectFinallyDeletedEvent
from plone.server.interfaces import IObjectFinallyModifiedEvent
from plone.server.interfaces import IObjectFinallyVisitedEvent
from plone.server.interfaces import IObjectPermissionsModifiedEvent
from plone.server.interfaces import IObjectPermissionsViewEvent
from plone.server.interfaces import IResource
from zope.component._api import getSiteManager
from zope.component.interfaces import ComponentLookupError
from zope.component.interfaces import IObjectEvent
from zope.event import subscribers as syncsubscribers
from zope.interface import implementer
from zope.interface.interfaces import ObjectEvent


_zone = tzlocal()

asyncsubscribers = []


@implementer(IObjectFinallyCreatedEvent)
class ObjectFinallyCreatedEvent(ObjectEvent):
    """An object has been created."""


@implementer(IObjectFinallyDeletedEvent)
class ObjectFinallyDeletedEvent(ObjectEvent):
    """An object has been deleted."""


@implementer(IObjectFinallyModifiedEvent)
class ObjectFinallyModifiedEvent(ObjectEvent):
    """An object has been modified."""


@implementer(IObjectFinallyVisitedEvent)
class ObjectFinallyVisitedEvent(ObjectEvent):
    """An object has been modified."""


@implementer(IObjectPermissionsViewEvent)
class ObjectPermissionsViewEvent(ObjectEvent):
    """An object has been modified."""


@implementer(IObjectPermissionsModifiedEvent)
class ObjectPermissionsModifiedEvent(ObjectEvent):
    """An object has been modified."""


@implementer(IFileFinishUploaded)
class FileFinishUploaded(ObjectEvent):
    """A file has finish uploading."""


@implementer(INewUserAdded)
class NewUserAdded(object):
    """An object has been created."""

    def __init__(self, user):
        self.user = user


@implementer(IBeforeJSONAssignedEvent)
class BeforeJSONAssignedEvent(object):
    """An object is going to be assigned to an attribute on another object."""

    def __init__(self, object, name, context):
        self.object = object
        self.name = name
        self.context = context


@configure.subscriber(for_=(IResource, IObjectFinallyModifiedEvent))
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


@configure.subscriber(for_=IObjectEvent)
async def object_event_notify(event):
    """Dispatch ObjectEvents to interested adapters."""
    try:
        sitemanager = getSiteManager()
    except ComponentLookupError:
        # Oh blast, no site manager. This should *never* happen!
        return []

    return await sitemanager.adapters.asubscribers((event.object, event), None)

asyncsubscribers.append(dispatch)

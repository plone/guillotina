from datetime import datetime
from dateutil.tz import tzlocal
from guillotina import configure
from guillotina.interfaces import IBeforeJSONAssignedEvent
from guillotina.interfaces import IFileFinishUploaded
from guillotina.interfaces import INewUserAdded
from guillotina.interfaces import IObjectFinallyCreatedEvent
from guillotina.interfaces import IObjectFinallyDeletedEvent
from guillotina.interfaces import IObjectFinallyModifiedEvent
from guillotina.interfaces import IObjectFinallyVisitedEvent
from guillotina.interfaces import IObjectPermissionsModifiedEvent
from guillotina.interfaces import IObjectPermissionsViewEvent
from guillotina.interfaces import IResource
from zope.component._api import getSiteManager
from zope.component.interfaces import ComponentLookupError
from zope.component.interfaces import IObjectEvent
from zope.event import subscribers as syncsubscribers
from zope.interface import implementer


_zone = tzlocal()

asyncsubscribers = []


@implementer(IObjectEvent)
class ObjectEvent(object):

    def __init__(self, object):
        self.object = object


@implementer(IObjectEvent)
class ObjectModifiedEvent(object):

    def __init__(self, object, payload={}):
        self.object = object
        self.payload = payload


@implementer(IObjectFinallyCreatedEvent)
class ObjectFinallyCreatedEvent(ObjectModifiedEvent):
    """An object has been created."""


@implementer(IObjectFinallyDeletedEvent)
class ObjectFinallyDeletedEvent(ObjectEvent):
    """An object has been deleted."""


@implementer(IObjectFinallyModifiedEvent)
class ObjectFinallyModifiedEvent(ObjectModifiedEvent):
    """An object has been modified."""


@implementer(IObjectFinallyVisitedEvent)
class ObjectFinallyVisitedEvent(ObjectEvent):
    """An object has been modified."""


@implementer(IObjectPermissionsViewEvent)
class ObjectPermissionsViewEvent(ObjectEvent):
    """An object has been modified."""


@implementer(IObjectPermissionsModifiedEvent)
class ObjectPermissionsModifiedEvent(ObjectModifiedEvent):
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

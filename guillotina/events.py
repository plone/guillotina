from datetime import datetime
from dateutil.tz import tzlocal
from guillotina import configure
from guillotina.interfaces import IFileFinishUploaded
from guillotina.interfaces import INewUserAdded
from guillotina.interfaces import IObjectAddedEvent
from guillotina.interfaces import IObjectModifiedEvent
from guillotina.interfaces import IObjectMovedEvent
from guillotina.interfaces import IObjectPermissionsModifiedEvent
from guillotina.interfaces import IObjectPermissionsViewEvent
from guillotina.interfaces import IObjectRemovedEvent
from guillotina.interfaces import IObjectVisitedEvent
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


@implementer(IObjectMovedEvent)
class ObjectMovedEvent(ObjectEvent):
    """An object has been moved"""

    def __init__(self, object, old_parent, old_name, new_parent, new_name, data=None):
        ObjectEvent.__init__(self, object)
        self.old_parent = old_parent
        self.old_name = old_name
        self.new_parent = new_parent
        self.new_name = new_name
        self.data = data


@implementer(IObjectAddedEvent)
class ObjectAddedEvent(ObjectMovedEvent):
    """An object has been added to a container"""

    def __init__(self, object, new_parent=None, new_name=None, data=None):
        if new_parent is None:
            new_parent = object.__parent__
        if new_name is None:
            new_name = object.__name__
        ObjectMovedEvent.__init__(self, object, None, None, new_parent, new_name, data=data)


@implementer(IObjectRemovedEvent)
class ObjectRemovedEvent(ObjectMovedEvent):
    """An object has been removed from a container"""

    def __init__(self, object, old_parent=None, old_name=None, data=None):
        if old_parent is None:
            old_parent = object.__parent__
        if old_name is None:
            old_name = object.__name__
        ObjectMovedEvent.__init__(self, object, old_parent, old_name, None, None)


@implementer(IObjectModifiedEvent)
class ObjectModifiedEvent(object):

    def __init__(self, object, payload={}):
        self.object = object
        self.payload = payload


@implementer(IObjectVisitedEvent)
class ObjectVisitedEvent(ObjectEvent):
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


@configure.subscriber(for_=(IResource, IObjectModifiedEvent))
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

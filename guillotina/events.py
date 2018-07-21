from guillotina.component.interfaces import IObjectEvent
from guillotina.interfaces import IBeforeObjectAddedEvent
from guillotina.interfaces import IBeforeObjectMovedEvent
from guillotina.interfaces import IBeforeObjectRemovedEvent
from guillotina.interfaces import IFileBeforeFinishUploaded
from guillotina.interfaces import IFileFinishUploaded
from guillotina.interfaces import IFileStartedUpload
from guillotina.interfaces import INewUserAdded
from guillotina.interfaces import IObjectAddedEvent
from guillotina.interfaces import IObjectDuplicatedEvent
from guillotina.interfaces import IObjectLoadedEvent
from guillotina.interfaces import IObjectLocationEvent
from guillotina.interfaces import IObjectModifiedEvent
from guillotina.interfaces import IObjectMovedEvent
from guillotina.interfaces import IObjectPermissionsModifiedEvent
from guillotina.interfaces import IObjectPermissionsViewEvent
from guillotina.interfaces import IObjectRemovedEvent
from guillotina.interfaces import IObjectVisitedEvent
from zope.interface import implementer


@implementer(IObjectEvent)
class ObjectEvent(object):

    def __init__(self, object, **kwargs):
        self.object = object
        self.data = kwargs


@implementer(IFileStartedUpload)
class FileUploadStartedEvent(ObjectEvent):
    pass


@implementer(IFileFinishUploaded)
class FileUploadFinishedEvent(ObjectEvent):
    pass


@implementer(IFileBeforeFinishUploaded)
class FileBeforeUploadFinishedEvent(ObjectEvent):
    pass


@implementer(IObjectLocationEvent)
class ObjectLocationEvent(ObjectEvent):
    """An object has been moved"""

    def __init__(self, object, old_parent, old_name, new_parent, new_name, payload=None):
        ObjectEvent.__init__(self, object)
        self.old_parent = old_parent
        self.old_name = old_name
        self.new_parent = new_parent
        self.new_name = new_name
        self.payload = payload


@implementer(IObjectMovedEvent)
class ObjectMovedEvent(ObjectLocationEvent):
    """An object has been moved"""


@implementer(IBeforeObjectMovedEvent)
class BeforeObjectMovedEvent(ObjectLocationEvent):
    pass


class BaseAddedEvent(ObjectLocationEvent):
    """An object has been added to a container"""

    def __init__(self, object, new_parent=None, new_name=None, payload=None):
        if new_parent is None:
            new_parent = object.__parent__
        if new_name is None:
            new_name = object.__name__
        super().__init__(object, None, None, new_parent, new_name,
                         payload=payload)


@implementer(IObjectAddedEvent)
class ObjectAddedEvent(BaseAddedEvent):
    """An object has been added to a container"""


@implementer(IObjectDuplicatedEvent)
class ObjectDuplicatedEvent(ObjectAddedEvent):
    def __init__(self, object, original_object, new_parent=None, new_name=None,
                 payload=None):
        super().__init__(object, new_parent, new_name, payload)


@implementer(IBeforeObjectAddedEvent)
class BeforeObjectAddedEvent(BaseAddedEvent):
    pass


class BaseObjectRemovedEvent(ObjectLocationEvent):
    """An object has been removed from a container"""

    def __init__(self, object, old_parent=None, old_name=None, payload=None):
        if old_parent is None:
            old_parent = object.__parent__
        if old_name is None:
            old_name = object.__name__
        super().__init__(object, old_parent, old_name, None, None)


@implementer(IObjectRemovedEvent)
class ObjectRemovedEvent(BaseObjectRemovedEvent):
    """An object has been removed from a container"""


@implementer(IBeforeObjectRemovedEvent)
class BeforeObjectRemovedEvent(BaseObjectRemovedEvent):
    pass


@implementer(IObjectModifiedEvent)
class ObjectModifiedEvent(object):

    def __init__(self, object, payload={}):
        self.object = object
        self.payload = payload


@implementer(IObjectLoadedEvent)
class ObjectLoadedEvent(ObjectEvent):
    """An object has been modified."""


@implementer(IObjectVisitedEvent)
class ObjectVisitedEvent(ObjectEvent):
    """An object has been modified."""


@implementer(IObjectPermissionsViewEvent)
class ObjectPermissionsViewEvent(ObjectEvent):
    """An object has been modified."""


@implementer(IObjectPermissionsModifiedEvent)
class ObjectPermissionsModifiedEvent(ObjectModifiedEvent):
    """An object has been modified."""


@implementer(INewUserAdded)
class NewUserAdded(object):
    """An object has been created."""

    def __init__(self, user):
        self.user = user

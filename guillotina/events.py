from guillotina.component.interfaces import IObjectEvent
from guillotina.db.orm.interfaces import IBaseObject
from guillotina.interfaces import IAfterAsyncUtilityLoadedEvent
from guillotina.interfaces import IApplicationCleanupEvent
from guillotina.interfaces import IApplicationConfiguredEvent
from guillotina.interfaces import IApplicationEvent
from guillotina.interfaces import IApplicationInitializedEvent
from guillotina.interfaces import IBeforeAsyncUtilityLoadedEvent
from guillotina.interfaces import IBeforeObjectAddedEvent
from guillotina.interfaces import IBeforeObjectModifiedEvent
from guillotina.interfaces import IBeforeObjectMovedEvent
from guillotina.interfaces import IBeforeObjectRemovedEvent
from guillotina.interfaces import IBeforeRenderViewEvent
from guillotina.interfaces import IDatabaseInitializedEvent
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
from guillotina.interfaces import IRegistry
from guillotina.interfaces import IRegistryEditedEvent
from guillotina.interfaces import ITraversalMissEvent
from guillotina.interfaces import ITraversalResourceMissEvent
from guillotina.interfaces import ITraversalRouteMissEvent
from guillotina.interfaces import ITraversalViewMissEvent
from guillotina.interfaces import IUserLogin
from guillotina.interfaces import IUserRefreshToken
from zope.interface import implementer

import typing


@implementer(IObjectEvent)
class ObjectEvent:
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


@implementer(IBeforeRenderViewEvent)
class BeforeRenderViewEvent:
    def __init__(self, request, view):
        self.request = request
        self.view = view


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
        super().__init__(object, None, None, new_parent, new_name, payload=payload)


@implementer(IObjectAddedEvent)
class ObjectAddedEvent(BaseAddedEvent):
    """An object has been added to a container"""


@implementer(IObjectDuplicatedEvent)
class ObjectDuplicatedEvent(ObjectAddedEvent):
    def __init__(self, object, original_object, new_parent=None, new_name=None, payload=None):
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


@implementer(IBeforeObjectModifiedEvent)
class BeforeObjectModifiedEvent(object):
    def __init__(self, object, payload=None):
        self.object = object
        self.payload = payload or {}


@implementer(IObjectModifiedEvent)
class ObjectModifiedEvent(object):
    def __init__(self, object, payload=None):
        self.object = object
        self.payload = payload or {}


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


@implementer(IUserLogin)
class UserLogin(object):
    """An object has logged in."""

    def __init__(self, user, token):
        self.user = user
        self.token = token


@implementer(IUserRefreshToken)
class UserRefreshToken(object):
    """An object has been created."""

    def __init__(self, user, token):
        self.user = user
        self.token = token


@implementer(IApplicationEvent)
class ApplicationEvent:
    def __init__(self, app, loop=None, **kwargs):
        self.app = app
        self.loop = loop
        self.data = kwargs


@implementer(IApplicationConfiguredEvent)
class ApplicationConfiguredEvent(ApplicationEvent):
    pass


@implementer(IApplicationInitializedEvent)
class ApplicationInitializedEvent(ApplicationEvent):
    pass


@implementer(IApplicationCleanupEvent)
class ApplicationCleanupEvent(ApplicationEvent):
    pass


@implementer(ITraversalMissEvent)
class TraversalMissEvent:
    def __init__(self, request, tail):
        self.request = request
        self.tail = tail


@implementer(ITraversalResourceMissEvent)
class TraversalResourceMissEvent(TraversalMissEvent):
    pass


@implementer(ITraversalViewMissEvent)
class TraversalViewMissEvent(TraversalMissEvent):
    pass


@implementer(ITraversalRouteMissEvent)
class TraversalRouteMissEvent(TraversalMissEvent):
    pass


@implementer(IDatabaseInitializedEvent)
class DatabaseInitializedEvent:
    def __init__(self, database):
        self.database = database


@implementer(IRegistryEditedEvent)
class RegistryEditedEvent(ObjectEvent):
    """
    Registry has been edited
    """

    def __init__(self, object: IBaseObject, registry: IRegistry, changes: typing.Dict):
        ObjectEvent.__init__(self, object)
        self.changes = changes


@implementer(IBeforeAsyncUtilityLoadedEvent)
class BeforeAsyncUtilityLoadedEvent:
    def __init__(self, name, config):
        self.name = name
        self.config = config


@implementer(IAfterAsyncUtilityLoadedEvent)
class AfterAsyncUtilityLoadedEvent:
    def __init__(self, name, config, utility, task):
        self.name = name
        self.config = config
        self.utility = utility
        self.task = task

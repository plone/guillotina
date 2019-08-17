from zope.interface import Attribute
from zope.interface import Interface
from zope.interface import interfaces


class IBeforeObjectModifiedEvent(interfaces.IObjectEvent):
    """
    Before an object has been modified
    """


class IObjectModifiedEvent(interfaces.IObjectEvent):
    """An object has been modified"""


class IObjectLocationEvent(interfaces.IObjectEvent):
    old_parent = Attribute("The old location parent for the object.")
    old_name = Attribute("The old location name for the object.")
    new_parent = Attribute("The new location parent for the object.")
    new_name = Attribute("The new location name for the object.")


class IObjectMovedEvent(IObjectLocationEvent):
    """An object has been moved."""


class IBeforeObjectMovedEvent(IObjectLocationEvent):
    """
    """


class IObjectAddedEvent(IObjectLocationEvent):
    """An object has been added to a container."""


class IObjectDuplicatedEvent(IObjectAddedEvent):
    """An object has been added to a container."""


class IObjectRemovedEvent(IObjectLocationEvent):
    """An object has been removed from a container."""


class IBeforeObjectAddedEvent(IObjectLocationEvent):
    """An object has been removed from a container."""


class IBeforeObjectRemovedEvent(IObjectLocationEvent):
    """An object has been removed from a container."""


class IObjectLoadedEvent(interfaces.IObjectEvent):
    """An objects has been loaded from the database"""


class IObjectVisitedEvent(interfaces.IObjectEvent):
    """An object has been vIContainerd."""


class IObjectPermissionsViewEvent(interfaces.IObjectEvent):
    """An object permissions has been vIContainerd."""


class IObjectPermissionsModifiedEvent(interfaces.IObjectEvent):
    """An object permissions has been modified."""


class IFileUploadEvent(interfaces.IObjectEvent):
    """
    """


class IFileStartedUpload(interfaces.IObjectEvent):
    """A file started uploading."""


class IFileBeforeFinishUploaded(interfaces.IObjectEvent):
    """Just before file is getting saved"""


class IFileFinishUploaded(interfaces.IObjectEvent):
    """A file has been finish uploaded."""


class INewUserAdded(Interface):
    """A new user created.

    The user is the id from the user logged in"""

    user = Attribute("User id created.")


class IUserLogin(Interface):
    """User logged in."""

    user = Attribute("User id logged in.")
    token = Attribute("Token issued.")


class IUserRefreshToken(Interface):
    """User refreshed token."""

    user = Attribute("User id refreshed.")
    token = Attribute("Token issued.")


class IApplicationEvent(Interface):
    app = Attribute("Server application object")
    loop = Attribute("")


class IApplicationConfiguredEvent(IApplicationEvent):
    """
    After guillotina has been configured
    """


class IApplicationInitializedEvent(IApplicationEvent):
    """
    After initialization of static files, keys
    and async utilities
    """


class IApplicationCleanupEvent(IApplicationEvent):
    """
    On app cleanup
    """


class ITraversalMissEvent(Interface):
    request = Attribute("Request object")
    tail = Attribute("Unresolvable part of the request path")


class ITraversalResourceMissEvent(ITraversalMissEvent):
    """
    When application was not able to resolve requested resource
    """


class ITraversalViewMissEvent(ITraversalMissEvent):
    """
    When application was not able to resolve requested route for resource
    """


class ITraversalRouteMissEvent(ITraversalMissEvent):
    """
    When application was not able to resolve requested route for resource
    """


class IDatabaseInitializedEvent(Interface):
    database = Attribute("")


class IBeforeRenderViewEvent(Interface):
    """Right before the view gets rendered
    """


class IRegistryEditedEvent(interfaces.IObjectEvent):
    """
    When registry edited
    """


class IBeforeAsyncUtilityLoadedEvent(Interface):
    """
    Right before async utility is loaded
    """


class IAfterAsyncUtilityLoadedEvent(Interface):
    """
    Right after async utility is loaded
    """

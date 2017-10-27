from zope.interface import Attribute
from zope.interface import Interface
from zope.interface import interfaces


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
    '''
    '''


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


class IFileFinishUploaded(interfaces.IObjectEvent):
    """A file has been finish uploaded."""


class INewUserAdded(Interface):
    """A new user logged in.

    The user is the id from the user logged in"""

    user = Attribute("User id created.")

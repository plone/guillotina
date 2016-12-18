from zope.interface import Attribute
from zope.interface import Interface
from zope.interface import interfaces


class IObjectFinallyCreatedEvent(interfaces.IObjectEvent):
    """An object has been created.

    The location will usually be ``None`` for this event."""


class IObjectFinallyDeletedEvent(interfaces.IObjectEvent):
    """An object has been deleted.

    The location will usually be ``None`` for this event."""


class IObjectFinallyModifiedEvent(interfaces.IObjectEvent):
    """An object has been modified.

    The location will usually be ``None`` for this event."""


class IObjectFinallyVisitedEvent(interfaces.IObjectEvent):
    """An object has been visited."""


class IObjectPermissionsViewEvent(interfaces.IObjectEvent):
    """An object permissions has been visited."""


class IObjectPermissionsModifiedEvent(interfaces.IObjectEvent):
    """An object permissions has been modified."""


class INewUserAdded(Interface):
    """A new user logged in.

    The user is the id from the user logged in"""

    user = Attribute("User id created.")

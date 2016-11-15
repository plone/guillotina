from datetime import datetime
from dateutil.tz import tzlocal
from plone.server.interfaces import INewUserAdded
from plone.server.interfaces import IObjectFinallyCreatedEvent
from zope.interface import implementer
from zope.interface.interfaces import ObjectEvent
_zone = tzlocal()


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

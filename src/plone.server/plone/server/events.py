
from plone.server.interfaces import INewUserAdded
from plone.server.interfaces import IObjectFinallyCreatedEvent
from zope.interface import implementer
from zope.interface.interfaces import ObjectEvent


@implementer(IObjectFinallyCreatedEvent)
class ObjectFinallyCreatedEvent(ObjectEvent):
    """An object has been created"""


@implementer(INewUserAdded)
class NewUserAdded(object):
    """An object has been created"""

    def __init__(self, user):
        self.user = user

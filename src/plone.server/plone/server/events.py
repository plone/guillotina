
from plone.server.interfaces import IObjectFinallyCreatedEvent
from zope.interface.interfaces import ObjectEvent
from zope.interface import implementer


@implementer(IObjectFinallyCreatedEvent)
class ObjectFinallyCreatedEvent(ObjectEvent):
    """An object has been created"""

from guillotina.db.interfaces import IStorageCreatedEvent
from zope.interface import implementer


@implementer(IStorageCreatedEvent)
class StorageCreatedEvent:
    def __init__(self, object, **kwargs):
        self.object = object
        self.options = kwargs

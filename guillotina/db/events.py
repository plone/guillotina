from zope.interface import implementer

from guillotina.db.interfaces import IStorageCreatedEvent


@implementer(IStorageCreatedEvent)
class StorageCreatedEvent:
    def __init__(self, object, **kwargs):
        self.object = object
        self.options = kwargs

from collections import UserDict
from guillotina import configure
from guillotina.db.interfaces import ITransaction
from guillotina.db.orm.base import BaseObject
from guillotina.exceptions import TransactionNotFound
from guillotina.interfaces import IAnnotationData
from guillotina.interfaces import IAnnotations
from guillotina.interfaces import IRegistry
from guillotina.interfaces import IResource
from guillotina.transactions import get_transaction
from zope.interface import implementer

import logging


logger = logging.getLogger("guillotina")
_marker = object()


@implementer(IAnnotationData)
class AnnotationData(BaseObject, UserDict):
    """
    store data on basic dictionary object but also inherit from base object
    """


@configure.adapter(for_=IRegistry, provides=IAnnotations)
@configure.adapter(for_=IResource, provides=IAnnotations)
class AnnotationsAdapter:
    """Store annotations on an object
    """

    def __init__(self, obj):
        self.obj = obj

    def get(self, key, default=None):
        """
        non-async variant
        """
        annotations = self.obj.__gannotations__
        if key in annotations:
            return annotations[key]
        return default

    async def async_get(self, key, default=None, reader=None):
        annotations = self.obj.__gannotations__
        element = annotations.get(key, _marker)
        if element is _marker:
            # Get from DB
            txn = self._get_transaction()
            if txn is not None:
                try:
                    obj = await txn.get_annotation(self.obj, key, reader=reader)
                except KeyError:
                    obj = None
                if obj is not None:
                    annotations[key] = obj
        if key in annotations:
            return annotations[key]
        return default

    async def async_keys(self):
        txn = self._get_transaction()
        return await txn.get_annotation_keys(self.obj.__uuid__)

    async def async_set(self, key, value):
        if not isinstance(value, BaseObject):
            raise KeyError("Not a valid object as annotation")
        annotations = self.obj.__gannotations__
        value.id = key  # make sure id is set...
        annotations[key] = value
        value.__of__ = self.obj.__uuid__
        value.__name__ = key
        value.__new_marker__ = True
        # we register the value
        txn = self._get_transaction()
        value.__txn__ = txn
        txn.register(value)
        logger.debug("registering annotation {}({}), of: {}".format(value.__uuid__, key, value.__of__))

    def _get_transaction(self) -> ITransaction:
        txn = get_transaction()
        if txn is not None:
            return txn
        if self.obj.__txn__ is not None:
            return self.obj.__txn__
        raise TransactionNotFound()

    async def async_del(self, key):
        annotation = await self.async_get(key)
        if annotation is not None:
            txn = self._get_transaction()
            txn.delete(annotation)
            if key in self.obj.__gannotations__:
                del self.obj.__gannotations__[key]

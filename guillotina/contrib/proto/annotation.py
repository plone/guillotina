from collections import UserDict
from guillotina import configure
from guillotina.db.interfaces import ITransaction
from guillotina.db.orm.base import BaseObject
from guillotina.exceptions import TransactionNotFound
from guillotina.contrib.proto.interfaces import IProtoData
from guillotina.interfaces import IRegistry
from guillotina.interfaces import IResource
from guillotina.transactions import get_transaction
from guillotina.contrib.proto.reader import reader as proto_reader
from zope.interface import implementer
from google.protobuf.json_format import MessageToDict

import logging


logger = logging.getLogger("guillotina")
_marker = object()


@implementer(IProtoData)
class ProtoData(BaseObject):
    """
    store data on basic dictionary object but also inherit from base object
    """

    __pb__ = None
    __plass__ = None

    def __set_plass__(self, plass):
        self.__plass__ = plass
        self.__pb__ = self.__plass__()

    def __getattribute__(self, name):
        try:
            return self.__pb__.__getattribute__(name)
        except AttributeError:
            return super().__getattribute__(name)(self)


    def __setattr__(self, name, value):
        try:
            return self.__pb__.__setattr__(name, value)
        except AttributeError:
            return super().__setattr__(name, value)

    def SerializeToString(self):
        return self.__pb__.SerializeToString()

    def ParseFromString(self, data):
        self.__pb__ = self.__pb__.ParseFromString(data)

    def MessageToDict(self):
        return MessageToDict(self.__pb__)

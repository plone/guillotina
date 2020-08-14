from zope.interface import Interface
from zope.interface import Attribute


class IProtoData(Interface):

    __pb__ = Attribute("Protobuffer object")
    __plass__ = Attribute("Class of proto python object")



class IProtoInterface(Interface):

    __plass__ = Attribute("Class of proto python object")

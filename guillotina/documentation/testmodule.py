from guillotina import schema
from zope.interface import Interface


class ISchema(Interface):
    foo = schema.TextLine()

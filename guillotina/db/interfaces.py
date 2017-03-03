from guillotina.interfaces import IContainer
from zope.interface import Interface


class IPartition(Interface):
    """Get the partition of the object"""


class IWriter(Interface):
    """Serializes the object for DB storage"""


class IContainer(IContainer):
    pass

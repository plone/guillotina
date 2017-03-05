from zope.interface import implements
from guillotina.db.interfaces import IPartition

@implements(IPartition)
class Partition(object):
    pass
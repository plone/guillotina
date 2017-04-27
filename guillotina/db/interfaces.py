from zope.interface import Interface


class IPartition(Interface):
    """Get the partition of the object"""


class IWriter(Interface):
    """Serializes the object for DB storage"""


class IConflictResolver(Interface):
    """resolve conflicts between 2 objects"""

    def resolve(self):
        pass

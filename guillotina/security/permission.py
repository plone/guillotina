from guillotina.component import get_utilities_for
from guillotina.interfaces import IPermission
from zope.interface import implementer


@implementer(IPermission)
class Permission(object):

    def __init__(self, id, title="", description=""):
        self.id = id
        self.title = title
        self.description = description


def get_all_permissions(context=None):
    """Get the ids of all defined permissions
    """
    for id, permission in get_utilities_for(IPermission, context):
        if id != 'zope.Public':
            yield id

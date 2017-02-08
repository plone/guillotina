from plone.server.auth.users import PloneUser
from plone.server import configure
from plone.server.transactions import get_current_request
from plone.server.interfaces import IGroups


class PloneGroup(PloneUser):
    def __init__(self, request, ident):
        super(PloneGroup, self).__init__(request)
        self.id = ident

        if ident == 'Managers':
            # Special Case its a Root Manager user
            self._roles['plone.SiteAdmin'] = 1
            self._roles['plone.SiteDeleter'] = 1
            self._roles['plone.Owner'] = 1
            self._roles['plone.Member'] = 1


@configure.utility(provides=IGroups)
class GroupsUtility(object):
    """ Class used to get groups. """

    def get_principal(self, ident):
        request = get_current_request()
        if not hasattr(request, '_cache_groups'):
            request._cache_groups = {}
        if ident not in request._cache_groups.keys():
            request._cache_groups[ident] = PloneGroup(request, ident)
        return request._cache_groups[ident]

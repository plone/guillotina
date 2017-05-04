from guillotina import configure
from guillotina.auth.users import GuillotinaUser
from guillotina.interfaces import IGroups
from guillotina.utils import get_current_request


class GuillotinaGroup(GuillotinaUser):
    def __init__(self, request, ident):
        super(GuillotinaGroup, self).__init__(request)
        self.id = ident

        if ident == 'Managers':
            # Special Case its a Root Manager user
            self._roles['guillotina.ContainerAdmin'] = 1
            self._roles['guillotina.ContainerDeleter'] = 1
            self._roles['guillotina.Owner'] = 1
            self._roles['guillotina.Member'] = 1
            self._roles['guillotina.Manager'] = 1


@configure.utility(provides=IGroups)
class GroupsUtility(object):
    """ Class used to get groups. """

    def get_principal(self, ident):
        request = get_current_request()
        if not hasattr(request, '_cache_groups'):
            request._cache_groups = {}
        if ident not in request._cache_groups.keys():
            request._cache_groups[ident] = GuillotinaGroup(request, ident)
        return request._cache_groups[ident]

from guillotina import configure
from guillotina.auth.users import GuillotinaUser
from guillotina.interfaces import IGroups
from guillotina.interfaces import IPrincipal

import typing


class GuillotinaGroup(GuillotinaUser):
    def __init__(self, ident, roles=None):
        if ident == "Managers":
            # Special Case its a Root Manager user
            roles = {
                "guillotina.ContainerAdmin": 1,
                "guillotina.ContainerDeleter": 1,
                "guillotina.Owner": 1,
                "guillotina.Member": 1,
                "guillotina.Manager": 1,
            }

        super(GuillotinaGroup, self).__init__(ident, roles=roles)


@configure.utility(provides=IGroups)
class GroupsUtility:
    """ Class used to get groups. """

    def get_principal(self, ident: str, principal: typing.Optional[IPrincipal]) -> IPrincipal:
        if principal is not None:
            try:
                cache = principal._groups_cache
            except AttributeError:
                cache = principal._groups_cache = {}
            if ident not in cache:
                cache[ident] = GuillotinaGroup(ident)
            return cache[ident]
        return GuillotinaGroup(ident)

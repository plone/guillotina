from guillotina import configure
from guillotina.auth.users import GuillotinaUser
from guillotina.interfaces import IGroups
from guillotina.interfaces import IPrincipal

import typing


class GuillotinaGroup(GuillotinaUser):
    def __init__(self, ident):
        super(GuillotinaGroup, self).__init__(ident)
        self.id = ident

        if ident == "Managers":
            # Special Case its a Root Manager user
            self._roles["guillotina.ContainerAdmin"] = 1
            self._roles["guillotina.ContainerDeleter"] = 1
            self._roles["guillotina.Owner"] = 1
            self._roles["guillotina.Member"] = 1
            self._roles["guillotina.Manager"] = 1


@configure.utility(provides=IGroups)
class GroupsUtility:
    """ Class used to get groups. """

    def get_principal(self, ident: str, principal: typing.Optional[IPrincipal]) -> IPrincipal:
        if principal is not None:
            cache = principal._groups_cache
            if ident not in cache:
                cache[ident] = GuillotinaGroup(ident)
            return cache[ident]
        return GuillotinaGroup(ident)

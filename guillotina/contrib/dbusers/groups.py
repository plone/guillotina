from collections import defaultdict
from guillotina.auth.groups import GuillotinaGroup
from guillotina.exceptions import ContainerNotFound
from guillotina.interfaces import IPrincipal
from guillotina.utils import get_current_container
from guillotina.utils import navigate_to

import typing


class DbUsersGroupsUtility:
    """ Class used to get groups. """

    def __init__(self):
        self._groups_by_container: typing.Dict[str, typing.Dict[str, GuillotinaGroup]] = defaultdict(dict)

    async def _get_group(self, ident: str) -> typing.Optional[GuillotinaGroup]:
        if ident == "Managers":
            group = GuillotinaGroup()
            # Special Case its a Root Manager user
            group._roles["guillotina.ContainerAdmin"] = 1
            group._roles["guillotina.ContainerDeleter"] = 1
            group._roles["guillotina.Owner"] = 1
            group._roles["guillotina.Member"] = 1
            group._roles["guillotina.Manager"] = 1
            return group
        else:
            container = get_current_container()
            try:
                group = await navigate_to(container, f"groups/{ident}")
            except KeyError:
                return None
            return GuillotinaGroup(ident, roles=group.roles)

    async def load_groups(self, groups: typing.Optional[typing.List[str]] = None) -> None:
        """
        Load group roles and permissions
        """
        try:
            container_id = get_current_container().id
        except ContainerNotFound:
            container_id = None
        for ident in groups or []:
            group = await self._get_group(ident)
            if group:
                self._groups_by_container[container_id][ident] = group

    def get_principal(self, ident: str, principal: typing.Optional[IPrincipal]) -> IPrincipal:
        try:
            container_id = get_current_container().id
        except ContainerNotFound:
            container_id = None
        return self._groups_by_container[container_id].get(ident) or GuillotinaGroup()

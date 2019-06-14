from guillotina import configure
from guillotina import task_vars
from guillotina.auth.users import GuillotinaUser
from guillotina.interfaces import IGroups


class GuillotinaGroup(GuillotinaUser):
    def __init__(self, ident):
        super(GuillotinaGroup, self).__init__(ident)
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
        groups = task_vars.authenticated_user_groups.get()
        if groups is None:
            groups = {}
            task_vars.authenticated_user_groups.set(groups)
        if ident not in groups:
            groups[ident] = GuillotinaGroup(ident)
        return groups[ident]

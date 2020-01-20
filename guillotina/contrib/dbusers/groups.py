from guillotina import configure
from guillotina.auth.groups import GuillotinaGroup
from guillotina.interfaces import IGroups


@configure.utility(provides=IGroups)
class GroupsUtility:
    """ Class used to get groups. """

    def get_principal(self, ident, principal=None):
        # import pdb; pdb.set_trace()
        if principal is not None:
            try:
                cache = principal._groups_cache
            except AttributeError:
                cache = principal._groups_cache = {}
            if ident not in cache:
                cache[ident] = GuillotinaGroup(ident)
            return cache[ident]
        return GuillotinaGroup(ident)

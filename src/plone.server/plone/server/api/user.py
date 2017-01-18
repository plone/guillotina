# -*- encoding: utf-8 -*-
from plone.server import configure
from plone.server.interfaces import ISite
from zope.authentication.interfaces import IAuthentication
from zope.component import getUtility


@configure.service(context=ISite, method='GET', permission='plone.AccessContent',
                   name='@user')
async def get_user_info(self):
    """Return information about the logged in user.
    """
    result = {}
    groups = set()
    for participation in self.request.security.participations:
        result[participation.principal.id] = {
            'roles': participation.principal._roles,
            'groups': participation.principal._groups,
            'properties': participation.principal._properties
        }
        groups.update(participation.principal._groups)

    group_search = getUtility(IAuthentication)
    result['groups'] = {}
    for group in groups:
        group_object = group_search.getPrincipal(group)
        result['groups'][group_object.id] = {
            'roles': group_object._roles,
            'groups': group_object._groups,
            'properties': group_object._properties
        }

    return result

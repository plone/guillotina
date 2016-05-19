# -*- coding: utf-8 -*-
from zope.security.checker import CheckerPublic
from zope.security.interfaces import IParticipation
from zope.security.management import system_user
from zope.security.proxy import removeSecurityProxy
from zope.securitypolicy.zopepolicy import ZopeSecurityPolicy

from plone.server.utils import get_current_request


class PloneSecurityPolicy(ZopeSecurityPolicy):

    def __init__(self, request=None, *args, **kwargs):
        if request is None:
            request = get_current_request()
        ZopeSecurityPolicy.__init__(self, *args, **kwargs)
        self.request = request
        participation = IParticipation(request)
        participation.interaction = self
        self.participations.append(participation)

    def checkPermission(self, permission, obj):
        if permission is CheckerPublic:
            return True

        obj = removeSecurityProxy(obj)
        seen = {}
        for participation in self.participations:
            principal = participation.principal
            if principal is None:
                continue

            if principal is system_user:
                return True

            if principal.id in seen:
                continue

            if self.cached_decision(
                    obj,
                    principal.id,
                    self._groupsFor(principal),
                    permission):
                return True

            seen[principal.id] = 1

        return False

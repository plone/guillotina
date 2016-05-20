# -*- coding: utf-8 -*-
from plone.server.interfaces import IRequest
from plone.server.utils import get_current_request
from zope.component import adapter
from zope.interface import implementer
from zope.security.checker import CheckerPublic
from zope.security.interfaces import IInteraction
from zope.security.management import system_user
from zope.securitypolicy.zopepolicy import ZopeSecurityPolicy
from zope.security.proxy import removeSecurityProxy


@adapter(IRequest)
@implementer(IInteraction)
def getCurrentInteraction(request):
    interaction = getattr(request, 'security', None)
    if IInteraction.providedBy(interaction):
        return interaction
    return Interaction(request)


class Interaction(ZopeSecurityPolicy):
    def __init__(self, request=None):
        ZopeSecurityPolicy.__init__(self)

        if request is not None:
            self.request = request
        else:
            # Try  magic request lookup if request not given
            self.request = get_current_request()

    def checkPermission(self, permission, obj):
        # Always allow public attributes
        if permission is CheckerPublic:
            return True

        # Remove implicit security proxy (if used)
        obj = removeSecurityProxy(obj)

        # Iterate through participations ('principals')
        # and check permissions they give
        seen = {}
        for participation in self.participations:
            principal = getattr(participation, 'principal', None)

            # Invalid participation (no principal)
            if principal is None:
                continue

            # System user always has access
            if principal is system_user:
                return True

            # Speed up by skipping seen principals
            if principal.id in seen:
                continue

            # Check the permission
            if self.cached_decision(
                    obj,
                    principal.id,
                    self._groupsFor(principal),
                    permission):
                return True

            seen[principal.id] = 1  # mark as seen

        return False

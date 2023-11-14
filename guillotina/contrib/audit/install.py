# -*- coding: utf-8 -*-
from guillotina import configure
from guillotina.addons import Addon
from guillotina.component import query_utility
from guillotina.contrib.audit.interfaces import IAuditUtility


@configure.addon(name="audit", title="Guillotina Audit using ES")
class ImageAddon(Addon):
    @classmethod
    async def install(cls, container, request):
        audit_utility = query_utility(IAuditUtility)
        await audit_utility.create_index()

    @classmethod
    async def uninstall(cls, container, request):
        pass

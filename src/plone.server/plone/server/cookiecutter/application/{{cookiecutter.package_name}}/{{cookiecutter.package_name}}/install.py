# -*- coding: utf-8 -*-
from plone.server.addons import Addon


class ManageAddon(Addon):

    @classmethod
    def install(cls, site, request):
        registry = request.site_settings
        # install logic here...

    @classmethod
    def uninstall(cls, site, request):
        registry = request.site_settings
        # uninstall logic here...

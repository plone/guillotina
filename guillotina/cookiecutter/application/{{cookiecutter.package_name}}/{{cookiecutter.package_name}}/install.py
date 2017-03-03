# -*- coding: utf-8 -*-
from guillotina.addons import Addon


class ManageAddon(Addon):

    @classmethod
    def install(cls, site, request):
        registry = request.site_settings  # noqa
        # install logic here...

    @classmethod
    def uninstall(cls, site, request):
        registry = request.site_settings  # noqa
        # uninstall logic here...

# -*- encoding: utf-8 -*-
from plone.server.interfaces import IAddOn
from zope.interface import implementer


@implementer(IAddOn)
class Addon(object):
    """ Prototype of an Addon plugin
    """

    @classmethod
    def install(self, request):
        pass

    @classmethod
    def uninstall(request):
        pass

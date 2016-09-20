# -*- encoding: utf-8 -*-
from zope.interface import implementer
from plone.server.interfaces import IAddOn


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

# -*- encoding: utf-8 -*-
from zope.interface import implementer
from plone.server.interfaces import IAddOn


@implementer(IAddOn)
class Addon(object):
    """ Prototype of an Addon plugin
    """

    def install(self, site):
        pass

    def uninstall(self):
        pass

from guillotina.interfaces import IAddOn
from zope.interface import implementer


@implementer(IAddOn)
class Addon(object):
    """ Prototype of an Addon plugin
    """

    @classmethod
    def install(cls, container, request):
        pass

    @classmethod
    def uninstall(cls, container, request):
        pass

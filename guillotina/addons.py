from guillotina.interface import implementer
from guillotina.interfaces import IAddOn


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

from zope.interface import Interface

from guillotina import configure, schema
from guillotina.addons import Addon


class IRegistryData(Interface):
    foobar = schema.TextLine()


@configure.addon(name="docaddon", title="Doc addon")
class TestAddon(Addon):
    @classmethod
    def install(cls, container, request):
        Addon.install(container, request)

    @classmethod
    def uninstall(cls, container, request):
        Addon.uninstall(container, request)

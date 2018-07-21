from guillotina import configure
from guillotina import schema
from guillotina.addons import Addon
from zope.interface import Interface


class IRegistryData(Interface):
    foobar = schema.TextLine()


@configure.addon(
    name="docaddon",
    title="Doc addon")
class TestAddon(Addon):
    @classmethod
    def install(cls, container, request):
        Addon.install(container, request)

    @classmethod
    def uninstall(cls, container, request):
        Addon.uninstall(container, request)

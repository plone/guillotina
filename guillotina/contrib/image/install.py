# -*- coding: utf-8 -*-
from guillotina import configure
from guillotina.addons import Addon
from guillotina.contrib.image.interfaces import IImagingSettings
from guillotina.utils import get_registry


@configure.addon(name="image", title="Guillotina Image field")
class ImageAddon(Addon):
    @classmethod
    async def install(cls, container, request):
        registry = await get_registry()
        registry.register_interface(IImagingSettings)
        registry.register()

    @classmethod
    async def uninstall(cls, container, request):
        pass

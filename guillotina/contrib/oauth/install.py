from guillotina import configure
from guillotina.addons import Addon
from guillotina.contrib.oauth.content import OAUTH_STORAGE_KEY, new_oauth_storage
from guillotina.contrib.oauth.interfaces import IOAuthSettings
from guillotina.interfaces import IAnnotations
from guillotina.utils import get_registry


@configure.addon(name="oauth", title="Guillotina OAuth authorization server")
class OAuthAddon(Addon):
    @classmethod
    async def install(cls, container, request):
        registry = await get_registry()
        registry.register_interface(IOAuthSettings)
        annotations = IAnnotations(container)
        if await annotations.async_get(OAUTH_STORAGE_KEY) is None:
            await annotations.async_set(OAUTH_STORAGE_KEY, new_oauth_storage())

    @classmethod
    async def uninstall(cls, container, request):
        annotations = IAnnotations(container)
        if await annotations.async_get(OAUTH_STORAGE_KEY) is not None:
            await annotations.async_del(OAUTH_STORAGE_KEY)

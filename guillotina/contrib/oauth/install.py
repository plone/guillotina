from guillotina import configure
from guillotina.addons import Addon
from guillotina.contrib.oauth.storage.access import get_oauth_store


@configure.addon(name="oauth", title="Guillotina OAuth authorization server")
class OAuthAddon(Addon):
    @classmethod
    async def install(cls, container, request):
        pass

    @classmethod
    async def uninstall(cls, container, request):
        store = get_oauth_store(container, require_installed=False)
        await store.delete_container_data()

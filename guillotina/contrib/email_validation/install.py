from guillotina import configure
from guillotina.addons import Addon
from guillotina.contrib.email_validation.interfaces import IValidationSettings
from guillotina.utils import get_registry


@configure.addon(name="email_validation", title="Guillotina Email Validation")
class EmailValidationAddon(Addon):
    @classmethod
    async def install(self, site, request):
        registry = await get_registry()
        registry.register_interface(IValidationSettings)

    @classmethod
    async def uninstall(self, site, request):
        pass

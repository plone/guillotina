from guillotina import configure
from guillotina.addons import Addon
from guillotina.contrib.mcp.interfaces import IMCPSettings
from guillotina.utils import get_registry


@configure.addon(name="mcp", title="Guillotina MCP integration")
class MCPAddon(Addon):
    @classmethod
    async def install(cls, container, request):
        registry = await get_registry()
        registry.register_interface(IMCPSettings)

    @classmethod
    async def uninstall(cls, container, request):
        pass

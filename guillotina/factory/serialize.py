from guillotina import configure
from guillotina.interfaces import IApplication
from guillotina.interfaces import IDatabase
from guillotina.interfaces import IRequest
from guillotina.interfaces import IResourceSerializeToJson
from guillotina.interfaces import IStaticDirectory
from guillotina.interfaces import IStaticFile
from guillotina.utils import get_security_policy


@configure.adapter(for_=(IDatabase, IRequest), provides=IResourceSerializeToJson)
class DatabaseToJson(object):
    def __init__(self, dbo, request):
        self.dbo = dbo

    async def __call__(self):
        keys = await self.dbo.async_keys()
        return {"containers": list(keys), "@type": "Database"}


@configure.adapter(for_=(IApplication, IRequest), provides=IResourceSerializeToJson)
class ApplicationToJson(object):
    def __init__(self, application, request):
        self.application = application
        self.request = request

    async def __call__(self):
        result = {"databases": [], "static_file": [], "static_directory": [], "@type": "Application"}
        allowed = get_security_policy().check_permission("guillotina.GetDatabases", self.application)

        for x in self.application._items.keys():
            if IDatabase.providedBy(self.application._items[x]) and allowed:
                result["databases"].append(x)
            if IStaticFile.providedBy(self.application._items[x]):
                result["static_file"].append(x)
            if IStaticDirectory.providedBy(self.application._items[x]):
                result["static_directory"].append(x)
        return result

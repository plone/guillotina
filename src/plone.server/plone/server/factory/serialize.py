from plone.server import configure
from plone.server.interfaces import IApplication
from plone.server.interfaces import IDatabase
from plone.server.interfaces import IRequest
from plone.server.interfaces import IResourceSerializeToJson
from plone.server.interfaces import IStaticDirectory
from plone.server.interfaces import IStaticFile


@configure.adapter(
    for_=(IDatabase, IRequest),
    provides=IResourceSerializeToJson)
class DatabaseToJson(object):

    def __init__(self, dbo, request):
        self.dbo = dbo

    def __call__(self):
        return {
            'sites': list(self.dbo.keys())
        }


@configure.adapter(
    for_=(IApplication, IRequest),
    provides=IResourceSerializeToJson)
class ApplicationToJson(object):

    def __init__(self, application, request):
        self.application = application
        self.request = request

    def __call__(self):
        result = {
            'databases': [],
            'static_file': [],
            'static_directory': []
        }

        allowed = self.request.security.checkPermission(
            'plone.GetDatabases', self.application)

        for x in self.application._dbs.keys():
            if IDatabase.providedBy(self.application._dbs[x]) and allowed:
                result['databases'].append(x)
            if IStaticFile.providedBy(self.application._dbs[x]):
                result['static_file'].append(x)
            if IStaticDirectory.providedBy(self.application._dbs[x]):
                result['static_directory'].append(x)
        return result

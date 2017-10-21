from guillotina._cache import BEHAVIOR_CACHE
from guillotina.browser import View
from guillotina.component import query_utility
from guillotina.component.interfaces import IFactory
from guillotina.interfaces import IAsyncBehavior
from guillotina.interfaces import IDownloadView
from guillotina.interfaces import ITraversableView
from zope.interface import alsoProvides


class Service(View):
    async def get_data(self):
        return await self.request.json()


class DownloadService(View):

    def __init__(self, context, request):
        super(DownloadService, self).__init__(context, request)
        alsoProvides(self, IDownloadView)


class TraversableService(View):

    def __init__(self, context, request):
        super(TraversableService, self).__init__(context, request)
        alsoProvides(self, ITraversableView)


class TraversableFieldService(View):
    async def publish_traverse(self, traverse):
        if len(traverse) == 1:
            # we want have the field
            name = traverse[0]
            fti = query_utility(IFactory, name=self.context.type_name)
            schema = fti.schema
            field = None
            self.behavior = None
            if name in schema:
                field = schema[name]
            else:
                # TODO : We need to optimize and move to content.py iterSchema
                for behavior_schema in fti.behaviors or ():
                    if name in behavior_schema:
                        field = behavior_schema[name]
                        self.behavior = behavior_schema(self.context)
                        break
                for behavior_name in self.context.__behaviors__ or ():
                    behavior_schema = BEHAVIOR_CACHE[behavior_name]
                    if name in behavior_schema:
                        field = behavior_schema[name]
                        self.behavior = behavior_schema(self.context)
                        break
            # Check that its a File Field
            if field is None:
                raise KeyError('No valid name')

            self.field = field.bind(self.behavior)
        else:
            self.field = None

        if (self.behavior is not None and
                IAsyncBehavior.implementedBy(self.behavior.__class__)):
            # providedBy not working here?
            await self.behavior.load()
        return self

    def __init__(self, context, request):
        super(TraversableFieldService, self).__init__(context, request)
        alsoProvides(self, ITraversableView)


class TraversableDownloadService(TraversableFieldService):

    def __init__(self, context, request):
        super(TraversableDownloadService, self).__init__(context, request)
        alsoProvides(self, IDownloadView)

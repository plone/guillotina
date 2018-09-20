from guillotina.response import HTTPNotFound
from guillotina._cache import BEHAVIOR_CACHE
from guillotina.browser import View
from guillotina.component import query_utility
from guillotina.component.interfaces import IFactory
from guillotina.interfaces import IAsyncBehavior


class Service(View):
    async def get_data(self):
        return await self.request.json()


class DownloadService(View):

    def __init__(self, context, request):
        super(DownloadService, self).__init__(context, request)


class TraversableFieldService(View):
    field = None

    async def prepare(self):
        # we want have the field
        name = self.request.matchdict['field_name']
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
            raise HTTPNotFound(content={
                'reason': 'No valid name'})

        if self.behavior is not None:
            self.field = field.bind(self.behavior)
        else:
            self.field = field.bind(self.context)

        if (self.behavior is not None and
                IAsyncBehavior.implementedBy(self.behavior.__class__)):
            # providedBy not working here?
            await self.behavior.load()

        return self

from guillotina._cache import BEHAVIOR_CACHE
from guillotina.browser import View
from guillotina.component import query_utility
from guillotina.component.interfaces import IFactory
from guillotina.fields import CloudFileField
from guillotina.interfaces import IAsyncBehavior
from guillotina.interfaces import ICloudFileField
from guillotina.response import HTTPNotFound
from guillotina.schema import Dict


class DictFieldProxy():

    def __init__(self, key, context, field_name):
        self.__key = key
        self.__context = context
        self.__field_name = field_name

    def __getattribute__(self, name):
        if name.startswith('_DictFieldProxy'):  # local attribute
            return super().__getattribute__(name)

        if name == self.__field_name:
            return getattr(self.__context, name).get(self.__key)
        else:
            return getattr(self.__context, name)

    def __setattr__(self, name, value):
        if name.startswith('_DictFieldProxy'):
            return super().__setattr__(name, value)

        if name == self.__field_name:
            getattr(self.__context, name)[self.__key] = value
        else:
            setattr(self.__context, name, value)


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
            ctx = self.behavior
        else:
            ctx = self.context

        if (self.behavior is not None and
                IAsyncBehavior.implementedBy(self.behavior.__class__)):
            # providedBy not working here?
            await self.behavior.load()

        if type(field) == Dict:
            key = self.request.matchdict['filename']
            self.field = CloudFileField(__name__=name).bind(
                DictFieldProxy(key, ctx, name)
            )
        elif ICloudFileField.providedBy(field):
            self.field = field.bind(ctx)

        if self.field is None:
            raise HTTPNotFound(content={
                'reason': 'No valid name'})

        return self

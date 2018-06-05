from guillotina.annotations import AnnotationData
from guillotina.interfaces import IAnnotationData
from guillotina.interfaces import IAnnotations
from guillotina.interfaces import IAsyncBehavior
from guillotina.interfaces import IContentBehavior
from zope.interface import implementer


_default = object()


@implementer(IAsyncBehavior)
class AnnotationBehavior:
    """A factory that knows how to store data in a separate object."""

    auto_serialize = True

    __local__properties__ = []

    # each annotation is stored
    __annotations_data_key__ = 'default'

    def __init__(self, context):
        self.__dict__['schema'] = [x for x in self.__implemented__][0]
        self.__dict__['prefix'] = self.__dict__['schema'].__identifier__ + '.'
        self.__dict__['data'] = {}
        self.__dict__['context'] = context

        # see if annotations are preloaded...
        annotations_container = IAnnotations(self.__dict__['context'])
        data = annotations_container.get(self.__annotations_data_key__, _default)
        if data is not _default:
            self.__dict__['data'] = data

    async def load(self, create=False):
        annotations_container = IAnnotations(self.__dict__['context'])
        data = annotations_container.get(self.__annotations_data_key__, _default)
        if data is not _default:
            # data is already preloaded, we do not need to get from db again...
            self.__dict__['data'] = data
            return

        annotations = await annotations_container.async_get(self.__annotations_data_key__)
        if annotations is None:
            if create:
                annotations = AnnotationData()
                await annotations_container.async_set(self.__annotations_data_key__, annotations)
            else:
                annotations = {}  # fallback, assumed only for reading here...
        self.__dict__['data'] = annotations

    def __getattr__(self, name):
        if (name not in self.__dict__['schema'] or
                name in self.__local__properties__):
            return super(AnnotationBehavior, self).__getattr__(name)

        key_name = self.__dict__['prefix'] + name
        data = self.__dict__['data']

        if key_name not in data:
            return self.__dict__['schema'][name].missing_value

        return data[key_name]

    def __setattr__(self, name, value):
        if (name not in self.__dict__['schema'] or
                name.startswith('__') or
                name.startswith('_v_') or
                name in self.__local__properties__ or
                name.startswith('_p_')):
            super(AnnotationBehavior, self).__setattr__(name, value)
        else:
            key = self.__dict__['prefix'] + name
            data = self.__dict__['data']
            data[key] = value
            if IAnnotationData.providedBy(data):
                data._p_register()

    def _p_register(self):
        if IAnnotationData.providedBy(self.__dict__['data']):
            self.__dict__['data']._p_register()


@implementer(IContentBehavior)
class ContextBehavior:
    """A factory that knows how to store data in a dict in the context."""
    auto_serialize = True

    def __init__(self, context):
        self.__dict__['schema'] = [x for x in self.__implemented__][0]
        self.__dict__['prefix'] = self.__dict__['schema'].__identifier__ + '.'
        self.__dict__['context'] = context

    async def load(self, create=False):
        '''
        implement interface so users of behaviors can be lazy
        '''
        pass

    def __getattr__(self, name):
        if name not in self.__dict__['schema']:
            raise AttributeError(name)

        context = self.__dict__['context']
        key_name = self.__dict__['prefix'] + name
        field = self.__dict__['schema'][name]
        if not hasattr(context, key_name):
            return field.missing_value

        return getattr(context, key_name, field.default)

    def __setattr__(self, name, value):
        if name not in self.__dict__['schema']:
            raise AttributeError(name)
        else:
            prefixed_name = self.__dict__['prefix'] + name
            self.__dict__['context'].__setattr__(prefixed_name, value)
            self.__dict__['context']._p_register()

    def _p_register(self):
        self.__dict__['context']._p_register()

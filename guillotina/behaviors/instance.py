# -*- coding: utf-8 -*-
from guillotina.annotations import AnnotationData
from guillotina.interfaces import IAnnotations
from guillotina.interfaces import IAsyncBehavior
from zope.interface import alsoProvides
from zope.interface import implementer
from zope.interface.declarations import Provides


@implementer(IAsyncBehavior)
class AnnotationBehavior(object):
    """A factory that knows how to store data in a separate object."""

    __local__properties__ = []

    # each annotation is stored
    __annotations_data_key = 'default'

    def __init__(self, context):
        self.__dict__['schema'] = [x for x in self.__implemented__][0]
        self.__dict__['prefix'] = self.__dict__['schema'].__identifier__ + '.'
        self.__dict__['data'] = {}
        self.__dict__['context'] = context
        self.__dict__['__provides__'] = Provides(self.__dict__['schema'])

    async def load(self, create=False):
        annotations_container = IAnnotations(self.__dict__['context'])
        annotations = {}
        try:
            annotations = await annotations_container.__getitem__(self.__annotations_data_key)
        except KeyError:
            if create:
                annotations = AnnotationData()
                await annotations_container.__setitem__(self.__annotations_data_key, annotations)
        self.__dict__['data'] = annotations

    def __getattr__(self, name):
        if name not in self.__dict__['schema']:
            return super(AnnotationBehavior, self).__getattr__(name)

        key_name = self.__dict__['prefix'] + name
        data = self.__dict__['data']

        if key_name not in data:
            return self.__dict__['schema'][name].missing_value

        return data[key_name]

    def __setattr__(self, name, value):
        if name not in self.__dict__['schema'] or \
                name in self.__local__properties__ or \
                name.startswith('__') or \
                name.startswith('_v_') or \
                name.startswith('_p_'):
            super(AnnotationBehavior, self).__setattr__(name, value)
        else:
            prefixed_name = self.__dict__['prefix'] + name
            data = self.__dict__['data']
            data[prefixed_name] = value


class ContextBehavior(object):
    """A factory that knows how to store data in a dict in the context."""

    def __init__(self, context):
        self.__dict__['schema'] = [x for x in self.__implemented__][0]
        self.__dict__['prefix'] = self.__dict__['schema'].__identifier__ + '.'
        self.__dict__['context'] = context
        alsoProvides(self, self.__dict__['schema'])

    def __getattr__(self, name):
        if name not in self.__dict__['schema']:
            raise AttributeError(name)

        context = self.__dict__['context']
        key_name = self.__dict__['prefix'] + name
        if hasattr(context, key_name):
            return self.__dict__['schema'][name].missing_value

        return context.__getattr__(key_name)

    def __setattr__(self, name, value):
        if name not in self.__dict__['schema']:
            raise AttributeError(name)
        else:
            prefixed_name = self.__dict__['prefix'] + name
            self.__dict__['context'].__setattr__(prefixed_name, value)

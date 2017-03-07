# -*- coding: utf-8 -*-
from guillotina.annotations import AnnotationData
from guillotina.interfaces import IAnnotations
from zope.interface import alsoProvides


class AnnotationBehavior(object):
    """A factory that knows how to store data in a separate object."""

    __local__properties__ = []

    # each annotation is stored
    __annotations_data_key = 'default'

    def __init__(self, context):
        self.__dict__['schema'] = [x for x in self.__implemented__][0]
        self.__dict__['prefix'] = self.__dict__['schema'].__identifier__ + '.'
        self.__dict__['annotations'] = IAnnotations(context)
        alsoProvides(self, self.__dict__['schema'])

    async def __getattr__(self, name):
        if name not in self.__dict__['schema']:
            raise AttributeError(name)

        key_name = self.__dict__['prefix'] + name
        annotations_container = self.__dict__['annotations']
        try:
            annotations = await annotations_container.__getitem__(self.__annotations_data_key)
        except KeyError:
            return self.__dict__['schema'][name].missing_value

        if key_name not in annotations:
            return self.__dict__['schema'][name].missing_value

        return annotations[key_name]

    async def __setattr__(self, name, value):
        if name not in self.__dict__['schema'] or \
                name in self.__local__properties__ or \
                name.startswith('__') or \
                name.startswith('_v_') or \
                name.startswith('_p_'):
            super(AnnotationBehavior, self).__setattr__(name, value)
        else:
            prefixed_name = self.__dict__['prefix'] + name
            annotations_container = self.__dict__['annotations']
            try:
                annotations = await annotations_container.__getitem__(self.__annotations_data_key)
            except KeyError:
                # create annotation data container here...
                annotations = AnnotationData()
                await annotations_container.__setitem__(self.__annotations_data_key, annotations)
            annotations[prefixed_name] = value


class ContextBehavior(object):
    """A factory that knows how to store data in a dict in the context."""

    def __init__(self, context):
        self.__dict__['schema'] = [x for x in self.__implemented__][0]
        self.__dict__['prefix'] = self.__dict__['schema'].__identifier__ + '.'
        self.__dict__['annotations'] = context
        alsoProvides(self, self.__dict__['schema'])

    def __getattr__(self, name):
        if name not in self.__dict__['schema']:
            raise AttributeError(name)

        annotations = self.__dict__['annotations']
        key_name = self.__dict__['prefix'] + name
        if hasattr(annotations, key_name):
            return self.__dict__['schema'][name].missing_value

        return annotations.__getattr__(key_name)

    def __setattr__(self, name, value):
        if name not in self.__dict__['schema']:
            raise AttributeError(name)
        else:
            prefixed_name = self.__dict__['prefix'] + name
            self.__dict__['annotations'].__setattr__(prefixed_name, value)

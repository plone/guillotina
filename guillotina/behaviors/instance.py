# -*- coding: utf-8 -*-
from zope.annotation.interfaces import IAnnotatable
from zope.annotation.interfaces import IAnnotations
from zope.component import adapter
from zope.interface import alsoProvides


@adapter(IAnnotatable)
class AnnotationBehavior(object):
    """A factory that knows how to store data in annotations."""

    __local__properties__ = []

    def __init__(self, context):
        self.__dict__['schema'] = [x for x in self.__implemented__][0]
        self.__dict__['prefix'] = self.__dict__['schema'].__identifier__ + '.'
        self.__dict__['annotations'] = IAnnotations(context)
        alsoProvides(self, self.__dict__['schema'])

    def __getattr__(self, name):
        if name not in self.__dict__['schema']:
            raise AttributeError(name)

        annotations = self.__dict__['annotations']
        key_name = self.__dict__['prefix'] + name
        if key_name not in annotations:
            return self.__dict__['schema'][name].missing_value

        return annotations[key_name]

    def __setattr__(self, name, value):
        if name not in self.__dict__['schema'] or \
                name in self.__local__properties__:
            super(AnnotationBehavior, self).__setattr__(name, value)
        else:
            prefixed_name = self.__dict__['prefix'] + name
            self.__dict__['annotations'][prefixed_name] = value

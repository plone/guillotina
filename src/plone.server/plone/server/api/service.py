# -*- coding: utf-8 -*-
from plone.server.browser import View
from plone.server.interfaces import IDownloadView
from plone.server.interfaces import ITraversableView
from zope.component import queryUtility
from zope.component.interfaces import IFactory
from zope.dottedname.resolve import resolve
from zope.interface import alsoProvides


class Service(View):
    pass


class DownloadService(View):

    def __init__(self, context, request):
        super(DownloadService, self).__init__(context, request)
        alsoProvides(self, IDownloadView)


class TraversableService(View):

    def __init__(self, context, request):
        super(TraversableService, self).__init__(context, request)
        alsoProvides(self, ITraversableView)


class TraversableFieldService(View):
    def publishTraverse(self, traverse):
        if len(traverse) == 1:
            # we want have the field
            name = traverse[0]
            fti = queryUtility(IFactory, name=self.context.portal_type)
            schema = fti.schema
            field = None
            if name in schema:
                field = schema[name]
            else:
                for behavior_schema in fti.behaviors or ():
                    if name in behavior_schema:
                        field = behavior_schema[name]
                        self.context = behavior_schema(self.context)
                        break
            # Check that its a File Field
            if field is None:
                raise KeyError('No valid name')

            self.field = field.bind(self.context)
        else:
            self.field = None
        return self

    def __init__(self, context, request):
        super(TraversableFieldService, self).__init__(context, request)
        alsoProvides(self, ITraversableView)


class TraversableDownloadService(TraversableFieldService):

    def __init__(self, context, request):
        super(TraversableDownloadService, self).__init__(context, request)
        alsoProvides(self, IDownloadView)

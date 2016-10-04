# -*- coding: utf-8 -*-
from plone.server.browser import View
from plone.server.interfaces import ITraversableView
from plone.server.interfaces import IDownloadView

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


class TraversableDownloadService(View):

    def __init__(self, context, request):
        super(TraversableDownloadService, self).__init__(context, request)
        alsoProvides(self, ITraversableView)
        alsoProvides(self, IDownloadView)

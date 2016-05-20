# -*- coding: utf-8 -*-
from plone.server.browser import View
from plone.server.interfaces import ITraversableView
from zope.interface import alsoProvides


class Service(View):
    pass


class TraversableService(View):

    def __init__(self, context, request):
        super(TraversableService, self).__init__(context, request)
        alsoProvides(self, ITraversableView)

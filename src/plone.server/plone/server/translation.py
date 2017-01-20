# -*- encoding: utf-8 -*-

from plone.server import configure
from plone.server.interfaces import ILanguage
from plone.server.interfaces import IRequest
from plone.server.interfaces import IResource
from plone.server.interfaces import ITranslated


@configure.adapter(
    for_=(ILanguage, IResource, IRequest),
    provides=ITranslated)
class GenericTranslation(object):

    def __init__(self, language, context, request):
        self.context = context
        self.language = language
        self.request = request

    def translate(self):
        return self.context

    def __call__(self):
        pass

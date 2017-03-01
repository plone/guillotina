# -*- encoding: utf-8 -*-

from guillotina import configure
from guillotina.interfaces import ILanguage
from guillotina.interfaces import IRequest
from guillotina.interfaces import IResource
from guillotina.interfaces import ITranslated


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

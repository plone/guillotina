# -*- encoding: utf-8 -*-

from plone.dexterity.interfaces import IDexterityContent
from plone.server.interfaces import ILanguage
from plone.server.interfaces import IRequest
from plone.server.interfaces import ITranslated
from zope.component import adapter
from zope.interface import implementer


@adapter(ILanguage, IDexterityContent, IRequest)
@implementer(ITranslated)
class GenericTranslation(object):

    def __init__(self, language, context, request):
        self.context = context
        self.language = language
        self.request = request

    def translate(self):
        return self.context

    def __call__(self):
        pass

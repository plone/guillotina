from guillotina import configure
from guillotina.interfaces import ILanguage
from guillotina.interfaces import ITranslated


@configure.adapter(for_=ILanguage, provides=ITranslated)
class GenericTranslation(object):

    def __init__(self, language, context=None, request=None):
        self.context = context
        self.language = language
        self.request = request

    def translate(self):
        return self.context

# -*- encoding: utf-8 -*-
from plone.dexterity.interfaces import IFormFieldProvider
from plone.supermodel import model
from zope import schema
from zope.interface import provider
from plone.dexterity.interfaces import IDexterityContent
from zope.component import adapter
from zope.dublincore.annotatableadapter import ZDCAnnotatableAdapter
from plone.server import _
from plone.server import DICT_LANGUAGES
from datetime import datetime
from dateutil.tz import tzlocal
from plone.server.interfaces import IAbsoluteUrl
from plone.uuid.interfaces import IUUID
from dateutil.tz import tzutc
from plone.dexterity.utils import safe_str
from zope.dublincore.interfaces import IWriteZopeDublinCore


from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from plone.i18n.locales.languages import _languagelist

OPTIONS = [
    SimpleTerm(value=_languagelist[l]['native'], token=l, title=_languagelist[l]['name']) for l in DICT_LANGUAGES.keys() if l in _languagelist
]
language_vocabulary = SimpleVocabulary(OPTIONS)
_zone = tzlocal()
_utc = tzutc()

# never expires
CEILING_DATE = datetime(*datetime.max.timetuple()[:-2], tzutc())
# always effective
FLOOR_DATE = datetime(*datetime.min.timetuple()[:-2], tzutc())

class ContextProperty(object):

    def __init__(self, attribute, default):
        self.__name__ = attribute
        self.default = default

    def __get__(self, inst, klass):
        if inst is None:
            return self

        if hasattr(inst.context, self.__name__):
            return getattr(inst.context, self.__name__, self.default)
        else:
            raise AttributeError('{field} not found on {context}'.format(
                field=self.__name__, context=str(inst.context)))

    def __set__(self, inst, value):
        if hasattr(inst.context, self.__name__):
            setattr(inst.context, self.__name__, value)
        else:
            raise AttributeError('{field} not found on {context}'.format(
                field=self.__name__, context=str(inst.context)))


@provider(IFormFieldProvider)
class IDublinCore(model.Schema, IWriteZopeDublinCore):
    pass


@adapter(IDexterityContent)
class DublinCore(ZDCAnnotatableAdapter):

    creators = ContextProperty(u'creators', ())
    contributors = ContextProperty(u'contributors', ())
    created = ContextProperty(u'creation_date', None)
    modified = ContextProperty(u'modification_date', None)

    def __init__(self, context):
        self.context = context
        super(DublinCore, self).__init__(context)
        self.expires = CEILING_DATE
        self.effective = FLOOR_DATE


# @provider(IFormFieldProvider)
# class IHistory(model.Schema):
#     """JSON stored versions"""

#     history = schema.List(
#         value_type=schema.Text(title=_(u'Version')),
#         title=u'History',
#         description="""A structure like 
#             {
#                 "user": "login",
#                 "time": "date",
#                 "modified": {
#                     "field1": "diff", # Text
#                     "field2": ["old", "new"] # Date/Number
#                 }
#             }
#         """
#         )


# @adapter(IDexterityContent)
# class History(ZDCAnnotatableAdapter):
#     pass

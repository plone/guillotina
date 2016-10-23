# -*- encoding: utf-8 -*-
from datetime import datetime
from dateutil.tz import tzlocal
from dateutil.tz import tzutc
from plone.dexterity.interfaces import IDexterityContent
from plone.dexterity.interfaces import IFormFieldProvider
from plone.dexterity.utils import safe_str
from plone.i18n.locales.languages import _languagelist
from plone.server import _
from plone.server import DICT_LANGUAGES
from plone.supermodel import model
from plone.supermodel.directives import catalog
from plone.supermodel.directives import index
from plone.uuid.interfaces import IUUID
from zope import schema
from zope.component import adapter
from zope.dublincore.annotatableadapter import ZDCAnnotatableAdapter
from zope.dublincore.interfaces import IWriteZopeDublinCore
from zope.interface import provider
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary
from plone.server.behaviors.properties import ContextProperty


OPTIONS = [
    SimpleTerm(value=_languagelist[l]['native'],
               token=l,
               title=_languagelist[l]['name'])
    for l in DICT_LANGUAGES.keys() if l in _languagelist
]
language_vocabulary = SimpleVocabulary(OPTIONS)
_zone = tzlocal()
_utc = tzutc()

# never expires
CEILING_DATE = datetime(*datetime.max.timetuple()[:-2], tzutc())
# always effective
FLOOR_DATE = datetime(*datetime.min.timetuple()[:-2], tzutc())


@provider(IFormFieldProvider)
class IDublinCore(model.Schema, IWriteZopeDublinCore):
    catalog(creators='text')
    catalog(subject='text')
    catalog(contributors='text')
    index(contributors='non_analyzed')
    index(creators='non_analyzed')
    index(subject='non_analyzed')


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

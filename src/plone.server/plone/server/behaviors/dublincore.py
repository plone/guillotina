# -*- encoding: utf-8 -*-
from datetime import datetime
from dateutil.tz import tzlocal
from dateutil.tz import tzutc
from plone.server import app_settings
from plone.server import configure
from plone.server.behaviors.properties import ContextProperty
from plone.server.directives import index
from plone.server.interfaces import IFormFieldProvider
from plone.server.interfaces import IResource
from plone.server.languages import _languagelist
from zope.component import adapter
from zope.dublincore.annotatableadapter import ZDCAnnotatableAdapter
from zope.dublincore.interfaces import IWriteZopeDublinCore
from zope.interface import Interface
from zope.interface import provider
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


OPTIONS = [
    SimpleTerm(value=_languagelist[l]['native'],
               token=l,
               title=_languagelist[l]['name'])
    for l in app_settings['languages'].keys() if l in _languagelist
]
language_vocabulary = SimpleVocabulary(OPTIONS)
_zone = tzlocal()
_utc = tzutc()

# never expires
CEILING_DATE = datetime(*datetime.max.timetuple()[:-2], tzutc())
# always effective
FLOOR_DATE = datetime(*datetime.min.timetuple()[:-2], tzutc())


class IMarkerDublinCore(Interface):
    """Marker interface for content with dublin core."""


@provider(IFormFieldProvider)
class IDublinCore(Interface, IWriteZopeDublinCore):
    index('creators', type='keyword')
    index('subject', type='keyword')
    index('contributors', type='keyword')


@configure.behavior(
    title="Dublin Core fields",
    provides=IDublinCore,
    marker=IMarkerDublinCore,
    for_="plone.server.interfaces.IResource")
class DublinCore(ZDCAnnotatableAdapter):

    creators = ContextProperty(u'creators', ())
    contributors = ContextProperty(u'contributors', ())
    created = ContextProperty(u'creation_date', None)
    modified = ContextProperty(u'modification_date', None)

    def __init__(self, context):
        self.context = context
        super(DublinCore, self).__init__(context)

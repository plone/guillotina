# -*- encoding: utf-8 -*-
from datetime import datetime
from dateutil.tz import tzlocal
from dateutil.tz import tzutc
from guillotina import configure
from guillotina import schema
from guillotina.behaviors.instance import AnnotationBehavior
from guillotina.behaviors.properties import ContextProperty
from guillotina.directives import index
from guillotina.interfaces import IFormFieldProvider
from zope.interface import Interface
from zope.interface import provider


_zone = tzlocal()
_utc = tzutc()

# never expires
CEILING_DATE = datetime(*datetime.max.timetuple()[:-2], tzutc())
# always effective
FLOOR_DATE = datetime(*datetime.min.timetuple()[:-2], tzutc())


class IMarkerDublinCore(Interface):
    """Marker interface for content with dublin core."""


@provider(IFormFieldProvider)
class IDublinCore(Interface):
    index('creators', type='keyword')
    index('tags', type='keyword')
    index('contributors', type='keyword')

    title = schema.TextLine(
        title=u'Title',
        description=u"The first unqualified Dublin Core 'Title' element value.")

    description = schema.Text(
        title=u'Description',
        description=u"The first unqualified Dublin Core 'Description' element value.")

    creation_date = schema.Datetime(
        title=u'Creation Date',
        description=u"The date and time that an object is created. "
                    u"\nThis is normally set automatically.")

    modification_date = schema.Datetime(
        title=u'Modification Date',
        description=u"The date and time that the object was last modified in a\n"
                    u"meaningful way.")

    effective_date = schema.Datetime(
        title=u'Effective Date',
        description=u"The date and time that an object should be published. ")

    expiration_date = schema.Datetime(
        title=u'Expiration Date',
        description=u"The date and time that the object should become unpublished.")

    creators = schema.Tuple(
        title=u'Creators',
        description=u"The unqualified Dublin Core 'Creator' element values",
        value_type=schema.TextLine())

    tags = schema.Tuple(
        title=u'Tags',
        description=u"The unqualified Dublin Core 'Tags' element values",
        value_type=schema.TextLine())

    publisher = schema.Text(
        title=u'Publisher',
        description=u"The first unqualified Dublin Core 'Publisher' element value.")

    contributors = schema.Tuple(
        title=u'Contributors',
        description=u"The unqualified Dublin Core 'Contributor' element values",
        value_type=schema.TextLine())


@configure.behavior(
    title="Dublin Core fields",
    provides=IDublinCore,
    marker=IMarkerDublinCore,
    for_="guillotina.interfaces.IResource")
class DublinCore(AnnotationBehavior):

    creators = ContextProperty('creators', ())
    contributors = ContextProperty('contributors', ())
    creation_date = ContextProperty('creation_date', None)
    modification_date = ContextProperty('modification_date', None)

    # all properties but these 4 are not annotated
    __local__properties__ = ('creation_date', 'modification_date',
                             'creators', 'contributors')

    def __init__(self, context):
        self.__dict__['context'] = context
        super(DublinCore, self).__init__(context)

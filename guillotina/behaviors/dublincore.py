from datetime import datetime
from dateutil.tz import tzutc
from guillotina import configure
from guillotina import schema
from guillotina.behaviors.instance import AnnotationBehavior
from guillotina.behaviors.properties import ContextProperty
from guillotina.directives import index_field
from zope.interface import Interface


_utc = tzutc()

# never expires
CEILING_DATE = datetime(*datetime.max.timetuple()[:-2], tzutc())  # type: ignore
# always effective
FLOOR_DATE = datetime(*datetime.min.timetuple()[:-2], tzutc())  # type: ignore


class IMarkerDublinCore(Interface):
    """Marker interface for content with dublin core."""


class IDublinCore(Interface):
    index_field('creators', type='keyword')
    index_field('tags', type='keyword')
    index_field('contributors', type='keyword')

    title = schema.TextLine(
        title=u'Title',
        description=u"The first unqualified Dublin Core 'Title' element value.",
        required=False)

    description = schema.Text(
        title=u'Description',
        description=u"The first unqualified Dublin Core 'Description' element value.",
        required=False)

    creation_date = schema.Datetime(
        title=u'Creation Date',
        description=u"The date and time that an object is created. "
                    u"\nThis is normally set automatically.",
        required=False)

    modification_date = schema.Datetime(
        title=u'Modification Date',
        description=u"The date and time that the object was last modified in a\n"
                    u"meaningful way.",
        required=False)

    effective_date = schema.Datetime(
        title=u'Effective Date',
        description=u"The date and time that an object should be published. ",
        required=False)

    expiration_date = schema.Datetime(
        title=u'Expiration Date',
        description=u"The date and time that the object should become unpublished.",
        required=False)

    creators = schema.Tuple(
        title=u'Creators',
        description=u"The unqualified Dublin Core 'Creator' element values",
        value_type=schema.TextLine(),
        required=False)

    tags = schema.Tuple(
        title=u'Tags',
        description=u"The unqualified Dublin Core 'Tags' element values",
        value_type=schema.TextLine(),
        required=False)

    publisher = schema.Text(
        title=u'Publisher',
        description=u"The first unqualified Dublin Core 'Publisher' element value.",
        required=False)

    contributors = schema.Tuple(
        title=u'Contributors',
        description=u"The unqualified Dublin Core 'Contributor' element values",
        value_type=schema.TextLine(),
        required=False)


@configure.behavior(
    title="Dublin Core fields",
    provides=IDublinCore,
    marker=IMarkerDublinCore,
    for_="guillotina.interfaces.IResource")
class DublinCore(AnnotationBehavior):
    auto_serialize = True

    title = ContextProperty('title', None)
    creators = ContextProperty('creators', ())
    contributors = ContextProperty('contributors', ())
    creation_date = ContextProperty('creation_date', None)
    modification_date = ContextProperty('modification_date', None)

    # all properties but these 4 are not annotated
    __local__properties__ = ('creation_date', 'modification_date',
                             'creators', 'contributors', 'title')

    def __init__(self, context):
        self.__dict__['context'] = context
        super(DublinCore, self).__init__(context)

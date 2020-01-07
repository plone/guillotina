from datetime import datetime
from dateutil.tz import tzutc
from guillotina import configure
from guillotina import schema
from guillotina.behaviors.instance import AnnotationBehavior
from guillotina.behaviors.properties import ContextProperty
from guillotina.directives import index_field
from guillotina.fields.patch import PatchField
from zope.interface import Interface


_utc = tzutc()

# never expires
CEILING_DATE = datetime(*datetime.max.timetuple()[:-2], tzutc())  # type: ignore
# always effective
FLOOR_DATE = datetime(*datetime.min.timetuple()[:-2], tzutc())  # type: ignore


class IMarkerDublinCore(Interface):
    """Marker interface for content with dublin core."""


class IDublinCore(Interface):
    index_field("creators", type="keyword")
    index_field("tags", type="keyword")
    index_field("contributors", type="keyword")

    title = schema.TextLine(
        title="Title", description="The first unqualified Dublin Core 'Title' element value.", required=False
    )

    description = schema.Text(
        title="Description",
        description="The first unqualified Dublin Core 'Description' element value.",
        required=False,
    )

    creation_date = schema.Datetime(
        title="Creation Date",
        description="The date and time that an object is created. " "\nThis is normally set automatically.",
        required=False,
    )

    modification_date = schema.Datetime(
        title="Modification Date",
        description="The date and time that the object was last modified in a\n" "meaningful way.",
        required=False,
    )

    effective_date = schema.Datetime(
        title="Effective Date",
        description="The date and time that an object should be published. ",
        required=False,
    )

    expiration_date = schema.Datetime(
        title="Expiration Date",
        description="The date and time that the object should become unpublished.",
        required=False,
    )

    creators = schema.Tuple(
        title="Creators",
        description="The unqualified Dublin Core 'Creator' element values",
        value_type=schema.TextLine(),
        required=False,
        naive=True,
        max_length=1000,
    )

    tags = PatchField(
        schema.Tuple(
            title="Tags",
            description="The unqualified Dublin Core 'Tags' element values",
            value_type=schema.TextLine(),
            required=False,
            naive=True,
            max_length=10000,
        )
    )

    publisher = schema.Text(
        title="Publisher",
        description="The first unqualified Dublin Core 'Publisher' element value.",
        required=False,
    )

    contributors = schema.Tuple(
        title="Contributors",
        description="The unqualified Dublin Core 'Contributor' element values",
        value_type=schema.TextLine(),
        required=False,
        naive=True,
        max_length=10000,
    )


@configure.behavior(
    title="Dublin Core fields",
    provides=IDublinCore,
    marker=IMarkerDublinCore,
    for_="guillotina.interfaces.IResource",
)
class DublinCore(AnnotationBehavior):
    auto_serialize = True

    title = ContextProperty("title", None)
    creators = ContextProperty("creators", ())
    contributors = ContextProperty("contributors", ())
    creation_date = ContextProperty("creation_date", None)
    modification_date = ContextProperty("modification_date", None)

    def __init__(self, context):
        self.__dict__["context"] = context
        super(DublinCore, self).__init__(context)

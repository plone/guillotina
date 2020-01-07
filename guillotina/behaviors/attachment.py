from guillotina import configure
from guillotina.fields import CloudFileField
from guillotina.schema import Dict
from guillotina.schema import TextLine
from zope.interface import Interface


class IAttachmentMarker(Interface):
    """Marker interface for content with attachments."""


class IMultiAttachmentMarker(Interface):
    """Marker interface for content with several attachments."""


@configure.behavior(
    title="Attachment behavior", marker=IAttachmentMarker, for_="guillotina.interfaces.IResource"
)
class IAttachment(Interface):
    file = CloudFileField()


@configure.behavior(
    title="MultiAttachment behavior", marker=IMultiAttachmentMarker, for_="guillotina.interfaces.IResource"
)
class IMultiAttachment(Interface):
    files = Dict(
        key_type=TextLine(), value_type=CloudFileField(), default={}, missing_value={}, max_length=1000
    )

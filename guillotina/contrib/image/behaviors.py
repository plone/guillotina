from collections import OrderedDict as NativeOrderedDict
from guillotina import configure
from guillotina.contrib.image.image import CloudImageFileField
from guillotina.schema import Dict
from guillotina.schema import OrderedDict
from guillotina.schema import TextLine
from zope.interface import Interface


class IImageAttachmentMarker(Interface):
    """Marker interface for content with image attachments."""


class IMultiImageAttachmentMarker(Interface):
    """Marker interface for content with several image attachments."""


class IMultiImageOrderedAttachmentMarker(Interface):
    """Marker interface for content with several ordered image attachments."""


@configure.behavior(
    title="ImageAttachment behavior", marker=IImageAttachmentMarker, for_="guillotina.interfaces.IResource"
)
class IImageAttachment(Interface):
    image = CloudImageFileField()


@configure.behavior(
    title="MultiImageAttachment behavior",
    marker=IMultiImageAttachmentMarker,
    for_="guillotina.interfaces.IResource",
)
class IMultiImageAttachment(Interface):
    images = Dict(
        key_type=TextLine(), value_type=CloudImageFileField(), default={}, missing_value={}, max_length=1000
    )


@configure.behavior(
    title="MultiImageAttachment behavior",
    marker=IMultiImageAttachmentMarker,
    for_="guillotina.interfaces.IResource",
)
class IMultiImageOrderedAttachment(Interface):
    images = OrderedDict(
        key_type=TextLine(),
        value_type=CloudImageFileField(),
        default=NativeOrderedDict(),
        missing_value=NativeOrderedDict(),
        max_length=1000,
    )

from guillotina import configure
from guillotina.behaviors.instance import AnnotationBehavior
from guillotina.fields import CloudFileField
from zope.interface import Interface


class IAttachmentMarker(Interface):
    """Marker interface for content with attachments."""


class IAttachment(Interface):
    file = CloudFileField()


@configure.behavior(
    title="Attachment behavior",
    provides=IAttachment,
    marker=IAttachmentMarker,
    for_="guillotina.interfaces.IResource")
class Attachment(AnnotationBehavior):
    pass

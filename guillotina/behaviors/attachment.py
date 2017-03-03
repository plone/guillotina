# -*- coding: utf-8 -*-
from guillotina import configure
from guillotina.files import BasicFileField
from guillotina.interfaces import IFormFieldProvider
from zope.interface import Interface
from zope.interface import provider


@provider(IFormFieldProvider)
class IAttachment(Interface):
    file = BasicFileField(
        title=u'File',
        required=False
    )


class IMarkerAttachment(Interface):
    """Marker interface for content with attachment."""


configure.behavior(
    title="Attachment",
    provides=IAttachment,
    marker=IMarkerAttachment,
    factory="guillotina.behaviors.instance.AnnotationBehavior",
    for_="guillotina.interfaces.IResource"
)()

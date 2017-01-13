# -*- coding: utf-8 -*-
from plone.server import configure
from plone.server.file import BasicFileField
from plone.server.interfaces import IFormFieldProvider
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
    factory="plone.behavior.AnnotationStorage",
    for_="plone.server.interfaces.IResource"
)()

# -*- coding: utf-8 -*-
from plone.server.behaviors.properties import AnnotationProperty
from plone.server.file import BasicFileField
from plone.server.interfaces import IFormFieldProvider
from plone.server.interfaces import IResource
from zope.component import adapter
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


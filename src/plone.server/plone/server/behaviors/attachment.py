# -*- coding: utf-8 -*-
from plone.server.behaviors.properties import ContextProperty
from plone.server.file import BasicFileField
from plone.server.interfaces import IFormFieldProvider
from plone.server.interfaces import IResource
from zope.component import adapter
from zope.dublincore.annotatableadapter import ZDCAnnotatableAdapter
from zope.interface import Interface
from zope.interface import provider


@provider(IFormFieldProvider)
class IAttachment(Interface):
    file = BasicFileField(
        title=u'File',
        required=False
    )


@adapter(IResource)
class Attachment(ZDCAnnotatableAdapter):

    file = ContextProperty(u'file', None)

    def __init__(self, context):
        self.context = context
        super(Attachment, self).__init__(context)

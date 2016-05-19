# -*- encoding: utf-8 -*-
from plone.dexterity.interfaces import IDexterityContent
from plone.dexterity.interfaces import IFormFieldProvider
from plone.server.api.service import Service
from plone.supermodel import model
from plone.supermodel.directives import read_permission
from zope import schema
from zope.component import adapter
from zope.dublincore.annotatableadapter import ZDCAnnotatableAdapter
from zope.dublincore.interfaces import IWriteZopeDublinCore
from zope.interface import provider


class ITodo(model.Schema):
    title = schema.TextLine(
        title='Title',
        required=False,
        description=u"Describe the task.",
        default=u''
    )
    done = schema.Bool(
        title='Done',
        required=False,
        description=u'Has the task been completed?',
        default=False
    )
    read_permission(notes='plone.example.classified')
    notes = schema.Text(
        title='Notes',
        required=False,
        description=u'Classified notes on about task',
        default=u''
    )


class View(Service):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    async def __call__(self):
        return {
            'context': str(self.context),
            'portal_type': self.context.portal_type,
        }


@provider(IFormFieldProvider)
class IDublinCore(IWriteZopeDublinCore):
    """We basically just want the IFormFieldProvider interface applied
        There's probably a zcml way of doing this. """


@adapter(IDexterityContent)
class DublinCore(ZDCAnnotatableAdapter):
    pass

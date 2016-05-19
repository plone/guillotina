# -*- encoding: utf-8 -*-
from plone.dexterity.interfaces import IDexterityContent
from plone.dexterity.interfaces import IFormFieldProvider
from plone.server.api.service import Service
from plone.supermodel import model
from zope import schema
from zope.component import adapter
from zope.dublincore.annotatableadapter import ZDCAnnotatableAdapter
from zope.dublincore.interfaces import IWriteZopeDublinCore
from zope.interface import provider


class ITodo(model.Schema):
    title = schema.TextLine(
        title=u"Title",
        required=False,
        description=u"It's a title",
    )
    done = schema.Bool(
        title=u"Done",
        required=False,
        description=u"Has the task been completed?",
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
    """ We basically just want the IFormFieldProvider interface applied
        There's probably a zcml way of doing this. """


@adapter(IDexterityContent)
class DublinCore(ZDCAnnotatableAdapter):
    pass

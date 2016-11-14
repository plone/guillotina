# -*- encoding: utf-8 -*-
from plone.server.content import Item
from plone.server.interfaces import IResource
from plone.server.interfaces import IFormFieldProvider
from plone.server.api.service import Service
from zope.interface import Interface
from plone.server.directives import read_permission
from plone.server.directives import fieldset

from zope import schema
from zope.component import adapter
from zope.dublincore.annotatableadapter import ZDCAnnotatableAdapter
from zope.interface import implementer
from zope.interface import provider


class IExampleBase(Interface):
    title = schema.TextLine(
        title='Title',
        required=False,
        description=u"Describe the task.",
        default=u''
    )


class ITodo(IExampleBase):
    done = schema.Bool(
        title='Done',
        required=False,
        description=u'Has the task been completed?',
        default=False
    )
    assigned_to = schema.TextLine(
        title='Assigned To',
        required=False,
        description=u"The person who needs to complete the task.",
        default=u''
    )
    read_permission(notes='plone.example.classified')
    notes = schema.Text(
        title='Notes',
        required=False,
        description=u'Classified notes about the task',
        default=u''
    )

    fieldset(u'other',
                   label=u'Additional Information',
                   fields=['assigned_to', 'notes'])


@implementer(ITodo)
class Todo(Item):
    pass


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
class IDublinCore(Interface):
    """We basically just want the IFormFieldProvider interface applied
        There's probably a zcml way of doing this. """
    created = schema.Datetime(
        title=u'Creation Date',
        description=u"The date and time that an object is created. "
                    u"\nThis is normally set automatically."
    )

    modified = schema.Datetime(
        title=u'Modification Date',
        description=u"The date and time that the object was last modified in a\n"
                    u"meaningful way."
    )


@adapter(IResource)
class DublinCore(ZDCAnnotatableAdapter):
    pass

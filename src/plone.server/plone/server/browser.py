# -*- coding: utf-8 -*-
from plone.dexterity.interfaces import IDexterityContent
from plone.server.interfaces import IRequest
from plone.server.interfaces import IView
from zope.component import adapter
from zope.interface import implementer
from zope.location import ILocation


def get_physical_path(context):
    parts = [context.__name__]
    parent = context.__parent__
    while parent is not None and parent.__name__ is not None:
        parts.append(parent.__name__)
        parent = parent.__parent__
    parts.append('')
    return reversed(parts)


@adapter(IDexterityContent, IRequest)
@implementer(IView, ILocation)
class View(object):

    __name__ = 'view'

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @property
    def __parent__(self):
        return self.context

    async def __call__(self):
        return {
            'context': str(self.context),
            'path': '/'.join(get_physical_path(self.context))
        }

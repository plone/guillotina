# -*- coding: utf-8 -*-
from plone.dexterity.interfaces import IDexterityContent
from plone.registry.interfaces import IRegistry
from plone.server.interfaces import IGET
from plone.server.interfaces import IRequest
from plone.server.interfaces import IView
from zope.component import adapter
from zope.interface import implementer


def get_physical_path(context):
    parts = [context.__name__]
    parent = context.__parent__
    while parent is not None and parent.__name__ is not None:
        parts.append(parent.__name__)
        parent = parent.__parent__
    parts.append('')
    return reversed(parts)


@adapter(IDexterityContent, IRequest)
@implementer(IView)
class View(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.registry = self.request.registry.getUtility(IRegistry)

    async def __call__(self):
        return {
            'context': str(self.context),
            'path': '/'.join(get_physical_path(self.context))
        }

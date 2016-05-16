# -*- encoding: utf-8 -*-
from zope.interface import Interface, Attribute
from plone.dexterity.fti import DexterityFTI
from aiohttp.web import Response
from venusianconfiguration import configure
from plone.server.content import Container
from zope.component.interfaces import ISite
from plone.registry.interfaces import IRegistry
from zope.component.persistentregistry import PersistentComponents
from zope.interface import implementer
from plone.server.interfaces import IView
from plone.server.interfaces import IRequest


class ITodo(Interface):

    title = Attribute("""Title""")

    done = Attribute("""Done""")


class View(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    async def __call__(self):
        registry = self.request.registry.getUtility(IRegistry)
        return Response(text=str(registry))
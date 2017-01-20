# -*- coding: utf-8 -*-
from plone.server import app_settings
from plone.server import configure
from plone.server.interfaces import IApplication
from plone.server.interfaces import IResourceSerializeToJson
from zope.component import getMultiAdapter


@configure.service(context=IApplication, method='GET', permission='plone.AccessContent')
async def get(context, request):
    serializer = getMultiAdapter(
        (context, request),
        IResourceSerializeToJson)
    return serializer()


@configure.service(context=IApplication, method='GET', permission='plone.GetPortals',
                   name='@apidefinition')
async def get_api_definition(context, request):
    return app_settings['api_definition']

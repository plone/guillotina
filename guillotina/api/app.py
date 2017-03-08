# -*- coding: utf-8 -*-
from guillotina import app_settings
from guillotina import configure
from guillotina.interfaces import IApplication
from guillotina.interfaces import IResourceSerializeToJson
from zope.component import getMultiAdapter


@configure.service(context=IApplication, method='GET', permission='guillotina.AccessContent')
async def get(context, request):
    serializer = getMultiAdapter(
        (context, request),
        IResourceSerializeToJson)
    return await serializer()


@configure.service(context=IApplication, method='GET', permission='guillotina.GetPortals',
                   name='@apidefinition')
async def get_api_definition(context, request):
    return app_settings['api_definition']

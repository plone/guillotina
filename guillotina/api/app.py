# -*- coding: utf-8 -*-
from guillotina import app_settings
from guillotina import configure
from guillotina.component import getMultiAdapter
from guillotina.interfaces import IApplication
from guillotina.interfaces import IResourceSerializeToJson


@configure.service(
    context=IApplication, method='GET', permission='guillotina.AccessContent',
    title="Get application data",
    description="Retrieves serialization of application")
async def get(context, request):
    serializer = getMultiAdapter(
        (context, request),
        IResourceSerializeToJson)
    return await serializer()


@configure.service(
    context=IApplication, method='GET', permission='guillotina.GetPortals',
    name='@apidefinition',
    title="Get API Definition",
    description="Retrieves information on API configuration")
async def get_api_definition(context, request):
    return app_settings['api_definition']

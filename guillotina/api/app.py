# -*- coding: utf-8 -*-
from guillotina import app_settings
from guillotina import configure
from guillotina.component import getMultiAdapter
from guillotina.interfaces import IApplication
from guillotina.interfaces import IResourceSerializeToJson


@configure.service(
    context=IApplication, method='GET', permission='guillotina.AccessContent',
    summary="Get application data",
    description="Retrieves serialization of application",
    responses={
        "200": {
            "description": "Application data",
            "schema": {
                "$ref": "#/definitions/Application"
            }
        }
    })
async def get(context, request):
    serializer = getMultiAdapter(
        (context, request),
        IResourceSerializeToJson)
    return await serializer()


@configure.service(
    context=IApplication, method='GET',
    permission='guillotina.GetContainers', name='@apidefinition',
    summary="Get API Definition",
    description="Retrieves information on API configuration")
async def get_api_definition(context, request):
    return app_settings['api_definition']

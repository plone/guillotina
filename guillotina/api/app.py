from guillotina import component
from guillotina import configure
from guillotina._settings import app_settings
from guillotina.component import get_multi_adapter
from guillotina.interfaces import IApplication
from guillotina.interfaces import IResourceSerializeToJson
from guillotina.utils import get_dotted_name


@configure.service(
    context=IApplication,
    method="GET",
    permission="guillotina.AccessContent",
    summary="Get application data",
    description="Retrieves serialization of application",
    responses={
        "200": {
            "description": "Application data",
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Application"}}},
        }
    },
)
async def get(context, request):
    serializer = get_multi_adapter((context, request), IResourceSerializeToJson)
    return await serializer()


@configure.service(
    context=IApplication,
    method="GET",
    permission="guillotina.GetContainers",
    name="@apidefinition",
    summary="Get API Definition",
    description="Retrieves information on API configuration",
)
async def get_api_definition(context, request):
    return app_settings["api_definition"]


@configure.service(
    context=IApplication,
    method="GET",
    name="@component-subscribers",
    permission="guillotina.ReadConfiguration",
    summary="Get all registered subscribers",
)
async def get_all_subscribers(context, request):
    subscribers = {}
    sm = component.get_global_components()
    for registration in sm.registeredHandlers():
        if len(registration.required) != 2:
            continue
        handler = get_dotted_name(registration.handler)
        event = get_dotted_name(registration.required[1])
        resource = get_dotted_name(registration.required[0])
        if resource not in subscribers:
            subscribers[resource] = {}
        if event not in subscribers[resource]:
            subscribers[resource][event] = []
        subscribers[resource][event].append(handler)
    return subscribers

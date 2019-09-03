from guillotina import addons
from guillotina import app_settings
from guillotina import configure
from guillotina import error_reasons
from guillotina import task_vars
from guillotina.api import content
from guillotina.api.service import Service
from guillotina.component import get_adapter
from guillotina.component import get_multi_adapter
from guillotina.content import create_content
from guillotina.event import notify
from guillotina.events import ObjectAddedEvent
from guillotina.interfaces import IAnnotations
from guillotina.interfaces import IApplication
from guillotina.interfaces import IContainer
from guillotina.interfaces import IDatabase
from guillotina.interfaces import IPrincipalRoleManager
from guillotina.interfaces import IResourceSerializeToJson
from guillotina.registry import REGISTRY_DATA_KEY
from guillotina.response import ErrorResponse
from guillotina.response import HTTPConflict
from guillotina.response import HTTPNotFound
from guillotina.response import HTTPNotImplemented
from guillotina.response import HTTPPreconditionFailed
from guillotina.response import Response
from guillotina.utils import get_authenticated_user_id
from typing import Optional

import posixpath


@configure.service(
    context=IDatabase,
    method="GET",
    permission="guillotina.GetContainers",
    summary="Get list of containers",
    responses={
        "200": {
            "description": "Get a list of containers",
            "content": {
                "application/json": {
                    "schema": {"properties": {"containers": {"type": "array", "items": {"type": "string"}}}}
                }
            },
        }
    },
)
class DefaultGET(Service):
    async def __call__(self):
        serializer = get_multi_adapter((self.context, self.request), IResourceSerializeToJson)
        return await serializer()


async def create_container(
    parent: IDatabase,
    container_id: str,
    container_type: str = "Container",
    owner_id: Optional[str] = None,
    emit_events: bool = True,
    **data,
):
    container = await create_content(container_type, id=container_id, **data)

    # Special case we don't want the parent pointer
    container.__name__ = container_id

    task_vars.container.set(container)
    await parent.async_set(container_id, container)
    await container.install()

    # Local Roles assign owner as the creator user
    if owner_id is not None:
        roleperm = IPrincipalRoleManager(container)
        roleperm.assign_role_to_principal("guillotina.Owner", owner_id)

    if emit_events:
        await notify(
            ObjectAddedEvent(container, parent, container.__name__, payload={"id": container.id, **data})
        )
    task_vars.container.set(container)
    return container


@configure.service(
    context=IDatabase,
    method="POST",
    permission="guillotina.AddContainer",
    summary="Create a new Container",
    description="Creates a new container on the database",
    validate=True,
    requestBody={
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "$ref": "#/components/schemas/BaseResource",
                    "properties": {"@addons": {"type": "string"}},
                }
            }
        },
    },
    responses={
        "200": {
            "description": "Container result",
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/BaseResource"}}},
        }
    },
)
class DefaultPOST(Service):
    """Create a new Container for DB Mounting Points."""

    async def __call__(self):
        data = await self.request.json()
        if "@type" not in data or data["@type"] not in app_settings["container_types"]:
            raise HTTPNotFound(content={"message": "can not create this type %s" % data["@type"]})

        if "id" not in data:
            raise HTTPPreconditionFailed(content={"message": "We need an id"})

        if not data.get("title"):
            data["title"] = data["id"]

        if "description" not in data:
            data["description"] = ""

        value = await self.context.async_contains(data["id"])

        if value:
            # Already exist
            raise HTTPConflict(content={"message": "Container with id already exists"})

        install_addons = data.pop("@addons", None) or []
        for addon in install_addons:
            # validate addon list
            if addon not in app_settings["available_addons"]:
                return ErrorResponse(
                    "RequiredParam",
                    "Property '@addons' must refer to a valid addon",
                    status=412,
                    reason=error_reasons.INVALID_ID,
                )

        owner_id = get_authenticated_user_id()

        container = await create_container(
            self.context, data.pop("id"), container_type=data.pop("@type"), owner_id=owner_id, **data
        )
        task_vars.container.set(container)

        annotations_container = get_adapter(container, IAnnotations)
        task_vars.registry.set(await annotations_container.async_get(REGISTRY_DATA_KEY))

        for addon in install_addons:
            await addons.install(container, addon)

        resp = {"@type": container.type_name, "id": container.id, "title": data["title"]}
        headers = {"Location": posixpath.join(self.request.path, container.id)}

        return Response(content=resp, headers=headers)


@configure.service(
    context=IContainer, method="DELETE", permission="guillotina.DeleteContainers", summary="Delete container"
)
class DefaultDELETE(content.DefaultDELETE):
    pass


@configure.service(context=IDatabase, method="DELETE", permission="guillotina.UmountDatabase", ignore=True)
@configure.service(context=IApplication, method="PUT", permission="guillotina.MountDatabase", ignore=True)
class NotImplemented(Service):
    async def __call__(self):
        raise HTTPNotImplemented(content={"message": "Function not implemented"}, status=501)

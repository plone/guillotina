from guillotina import configure
from guillotina.api import content
from guillotina.api.service import Service
from guillotina.component import get_multi_adapter
from guillotina.content import create_content
from guillotina.event import notify
from guillotina.events import ObjectAddedEvent
from guillotina.interfaces import IApplication
from guillotina.interfaces import IContainer
from guillotina.interfaces import IDatabase
from guillotina.interfaces import IPrincipalRoleManager
from guillotina.interfaces import IResourceSerializeToJson
from guillotina.response import HTTPConflict
from guillotina.response import HTTPNotFound
from guillotina.response import HTTPNotImplemented
from guillotina.response import HTTPPreconditionFailed
from guillotina.response import Response
from guillotina.utils import get_authenticated_user_id

import posixpath


@configure.service(
    context=IDatabase, method='GET', permission='guillotina.GetContainers',
    summary='Get list of containers',
    responses={
        "200": {
            "description": "Get a list of containers",
            "schema": {
                "properties": {
                    "containers": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                }
            }
        }
    })
class DefaultGET(Service):
    async def __call__(self):
        serializer = get_multi_adapter(
            (self.context, self.request),
            IResourceSerializeToJson)
        return await serializer()


@configure.service(
    context=IDatabase, method='POST', permission='guillotina.AddContainer',
    summary="Create a new Container",
    description="Creates a new container on the database",
    parameters=[{
        "name": "body",
        "in": "body",
        "schema": {
            "$ref": "#/definitions/BaseResource"
        }
    }],
    responses={
        "200": {
            "description": "Container result",
            "schema": {
                "$ref": "#/definitions/BaseResource"
            }
        }
    })
class DefaultPOST(Service):
    """Create a new Container for DB Mounting Points."""

    async def __call__(self):
        data = await self.request.json()
        if '@type' not in data or data['@type'] != 'Container':
            raise HTTPNotFound(content={
                'message': 'can not create this type %s' % data['@type']
            })

        if 'id' not in data:
            raise HTTPPreconditionFailed(content={
                'message': 'We need an id'
            })

        if not data.get('title'):
            data['title'] = data['id']

        if 'description' not in data:
            data['description'] = ''

        value = await self.context.async_contains(data['id'])

        if value:
            # Already exist
            raise HTTPConflict(content={
                'message': 'Container with id already exists'
            })

        container = await create_content(
            'Container',
            id=data['id'],
            title=data['title'],
            description=data['description'])

        # Special case we don't want the parent pointer
        container.__name__ = data['id']

        await self.context.async_set(data['id'], container)
        await container.install()

        self.request._container_id = container.__name__
        self.request.container = container

        user = get_authenticated_user_id(self.request)

        # Local Roles assign owner as the creator user
        roleperm = IPrincipalRoleManager(container)
        roleperm.assign_role_to_principal(
            'guillotina.Owner',
            user)

        await notify(ObjectAddedEvent(container, self.context, container.__name__,
                                      payload=data))

        resp = {
            '@type': 'Container',
            'id': data['id'],
            'title': data['title']
        }
        headers = {
            'Location': posixpath.join(self.request.path, data['id'])
        }

        return Response(content=resp, headers=headers)


@configure.service(
    context=IContainer, method='DELETE', permission='guillotina.DeleteContainers',
    summary='Delete container')
class DefaultDELETE(content.DefaultDELETE):
    pass


@configure.service(
    context=IDatabase, method='DELETE', permission='guillotina.UmountDatabase', ignore=True)
@configure.service(
    context=IApplication, method='PUT', permission='guillotina.MountDatabase', ignore=True)
class NotImplemented(Service):
    async def __call__(self):
        raise HTTPNotImplemented(
            content={
                'message': 'Function not implemented'
            }, status=501)

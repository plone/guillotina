# -*- coding: utf-8 -*-
from guillotina import configure
from guillotina.api import content
from guillotina.api.service import Service
from guillotina.browser import ErrorResponse
from guillotina.browser import Response
from guillotina.component import getMultiAdapter
from guillotina.content import create_content
from guillotina.event import notify
from guillotina.events import ObjectAddedEvent
from guillotina.interfaces import IApplication
from guillotina.interfaces import IDatabase
from guillotina.interfaces import IPrincipalRoleManager
from guillotina.interfaces import IResourceSerializeToJson
from guillotina.interfaces import IContainer
from guillotina.utils import get_authenticated_user_id


@configure.service(context=IDatabase, method='GET', permission='guillotina.GetPortals')
class DefaultGET(Service):
    async def __call__(self):
        serializer = getMultiAdapter(
            (self.context, self.request),
            IResourceSerializeToJson)
        return await serializer()


@configure.service(
    context=IDatabase, method='POST', permission='guillotina.AddPortal',
    title="Create a new Portal",
    description="Creates a new container on the database",
    payload={
        "query": {},
        "payload": {
            "@type": "string",
            "title": "string",
            "id": "string"
        },
        "traversal": []
    })
class DefaultPOST(Service):
    """Create a new Container for DB Mounting Points."""

    async def __call__(self):
        data = await self.request.json()
        if '@type' not in data and data['@type'] != 'Container':
            return ErrorResponse(
                'NotAllowed',
                'can not create this type %s' % data['@type'],
                status=401)

        if 'title' not in data and not data['title']:
            return ErrorResponse(
                'NotAllowed',
                'We need a title',
                status=401)

        if 'id' not in data:
            return ErrorResponse(
                'NotAllowed',
                'We need an id',
                status=401)

        if 'description' not in data:
            data['description'] = ''

        value = await self.context.async_contains(data['id'])

        if value:
            # Already exist
            return ErrorResponse(
                'NotAllowed',
                'Duplicate id',
                status=401)

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

        user = get_authenticated_user_id(self.request)

        # Local Roles assign owner as the creator user
        roleperm = IPrincipalRoleManager(container)
        roleperm.assign_role_to_principal(
            'guillotina.Owner',
            user)

        await notify(ObjectAddedEvent(container, self.context, container.__name__))

        resp = {
            '@type': 'Container',
            'id': data['id'],
            'title': data['title']
        }
        headers = {
            'Location': self.request.path + data['id']
        }

        return Response(response=resp, headers=headers)


class DefaultPUT(Service):
    pass


class DefaultPATCH(Service):
    pass


class SharingPOST(Service):
    pass


@configure.service(context=IContainer, method='DELETE', permission='guillotina.DeletePortals')
class DefaultDELETE(content.DefaultDELETE):
    pass


@configure.service(context=IDatabase, method='DELETE', permission='guillotina.UmountDatabase')
@configure.service(context=IApplication, method='PUT', permission='guillotina.MountDatabase')
class NotImplemented(Service):
    async def __call__(self):
        return ErrorResponse(
            'NotImplemented',
            'Function not implemented',
            status=501)

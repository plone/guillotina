# -*- coding: utf-8 -*-
from plone.server import configure
from plone.server.api.service import Service
from plone.server.browser import ErrorResponse
from plone.server.browser import Response
from plone.server.content import create_content
from plone.server.events import notify
from plone.server.events import ObjectFinallyCreatedEvent
from plone.server.interfaces import IApplication
from plone.server.interfaces import IDatabase
from plone.server.interfaces import ISite
from plone.server.interfaces import IResourceSerializeToJson
from plone.server.utils import get_authenticated_user_id
from zope.component import getMultiAdapter
from plone.server.interfaces import IPrincipalRoleManager


@configure.service(context=IDatabase, method='GET', permission='plone.GetPortals')
class DefaultGET(Service):
    async def __call__(self):
        serializer = getMultiAdapter(
            (self.context, self.request),
            IResourceSerializeToJson)
        return serializer()


@configure.service(
    context=IDatabase, method='POST', permission='plone.AddPortal',
    title="Create a new Portal",
    description="Creates a new site on the database",
    params={
        "query": {},
        "payload": {
            "@type": "string",
            "title": "string",
            "id": "string"
        },
        "traversal": []
    })
class DefaultPOST(Service):
    """Create a new Site for DB Mounting Points."""

    async def __call__(self):
        data = await self.request.json()
        if '@type' not in data and data['@type'] != 'Site':
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

        if data['id'] in self.context:
            # Already exist
            return ErrorResponse(
                'NotAllowed',
                'Duplicate id',
                status=401)

        site = create_content(
            'Site',
            id=data['id'],
            title=data['title'],
            description=data['description'])

        # Special case we don't want the parent pointer
        site.__name__ = data['id']

        self.context[data['id']] = site

        site.install()

        self.request._site_id = site.__name__

        user = get_authenticated_user_id(self.request)

        # Local Roles assign owner as the creator user
        roleperm = IPrincipalRoleManager(site)
        roleperm.assign_role_to_principal(
            'plone.Owner',
            user)

        await notify(ObjectFinallyCreatedEvent(site))
        # await notify(ObjectAddedEvent(site, self.context, site.__name__))

        resp = {
            '@type': 'Site',
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


@configure.service(context=ISite, method='DELETE', permission='plone.DeletePortals')
class DefaultDELETE(Service):
    async def __call__(self):
        portal_id = self.context.id
        del self.request.conn.root()[portal_id]
        return {}


@configure.service(context=IDatabase, method='DELETE', permission='plone.UmountDatabase')
@configure.service(context=IApplication, method='PUT', permission='plone.MountDatabase')
class NotImplemented(Service):
    async def __call__(self):
        return ErrorResponse(
            'NotImplemented',
            'Function not implemented',
            status=501)

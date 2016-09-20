# -*- coding: utf-8 -*-
from plone.jsonserializer.interfaces import ISerializeToJson
from plone.server.api.service import Service
from plone.server.browser import get_physical_path
from plone.server.browser import Response
from plone.server.browser import ErrorResponse
from zope.component import getMultiAdapter
from plone.dexterity.utils import createContent
from aiohttp.web_exceptions import HTTPUnauthorized, HTTPConflict


class DefaultGET(Service):
    async def __call__(self):
        serializer = getMultiAdapter(
            (self.context, self.request),
            ISerializeToJson)
        return serializer()


class DefaultPOST(Service):
    """ Creates a new Site for DB Mounting Points
    """
    async def __call__(self):
        data = await self.request.json()
        if '@type' not in data and data['@type'] != 'Plone Site':
            return HTTPUnauthorized('Not allowed type %s' % data['@type'])

        if 'title' not in data and not data['title']:
            return HTTPUnauthorized('Not allowed empty title')

        if 'id' not in data:
            data['id'] = 'ttt'

        if 'description' not in data:
            data['description'] = ''

        if data['id'] in self.context:
            # Already exist
            return HTTPConflict(reason="id already exist")

        site = createContent(
            'Plone Site',
            id=data['id'],
            title=data['title'],
            description=data['description'])

        self.context[data['id']] = site

        site.install()

        resp = {
            '@type': 'Plone Site',
            'id': data['id'],
            'title': data['title']
        }
        headers = {
            'Location': '/plone/ttt'
        }

        return Response(response=resp, headers=headers)


class DefaultPUT(Service):
    pass


class DefaultPATCH(Service):
    pass


class SharingPOST(Service):
    pass


class DefaultDELETE(Service):
    async def __call__(self):
        portal_id = self.context.id
        del self.request.conn.root()[portal_id]


class NotImplemented(Service):
    async def __call__(self):
        return ErrorResponse(
            'NotImplemented',
            'Function not implemented',
            status=501)

# -*- coding: utf-8 -*-
from plone.jsonserializer.interfaces import ISerializeToJson
from plone.jsonserializer.interfaces import IDeserializeFromJson
from plone.server.api.service import Service
from plone.server.registry import ICors
from plone.server.browser import get_physical_path
from zope.component import getMultiAdapter
from plone.server.browser import Response
from plone.server.browser import ErrorResponse
from plone.server.browser import UnauthorizedResponse
from plone.server.interfaces import IAbsoluteUrl
from plone.server import _
import fnmatch
from zope.security import checkPermission
from zope.security.interfaces import Unauthorized
from plone.dexterity.utils import createContent
from zope.component import queryMultiAdapter
import traceback
from datetime import datetime
import logging


logger = logging.getLogger(__name__)


class DefaultGET(Service):
    async def __call__(self):
        serializer = getMultiAdapter(
            (self.context, self.request),
            ISerializeToJson)
        return serializer()


class DefaultPOST(Service):
    async def __call__(self):
        """To create a content. Its a copy of plone.restapi"""
        import pdb; pdb.set_trace()
        data = await self.request.json()
        type_ = data.get('@type', None)
        id_ = data.get('id', None)
        title = data.get('title', None)

        if not type_:
            return ErrorResponse(
                'RequiredParam',
                _("Property '@type' is required"))

        # Generate a temporary id if the id is not given
        if not id_:
            now = datetime.now()
            new_id = '{}.{}.{}{:04d}'.format(
                type_.lower().replace(' ', '_'),
                now.strftime('%Y-%m-%d'),
                str(now.millis())[7:],
                randint(0, 9999))
        else:
            new_id = id_

        # It already exists
        if new_id in self.context:
            return ErrorResponse(
                'Conflict',
                _("Id already exists"))

        # Create object
        try:
            obj = createContent(type_, id=new_id, title=title)
            self.context[new_id] = obj
        except ValueError as e:
            return ErrorResponse(
                'DeserializationError',
                str(e),
                status=400)

        # Update fields
        deserializer = queryMultiAdapter((obj, self.request),
                                         IDeserializeFromJson)
        if deserializer is None:
            return ErrorResponse(
                'DeserializationError',
                'Cannot deserialize type {}'.format(obj.portal_type),
                status=501)

        try:
            deserializer(data, validate_all=True)
        except DeserializationError as e:
            return ErrorResponse(
                'DeserializationError',
                str(e),
                status=400)

        # Rename if generated id
        if not id_:
            self.rename_object(obj)

        absolute_url = queryMultiAdapter((obj, self.request), IAbsoluteUrl)

        headers = {
            'Location': await absolute_url()
        }
        return Response(response={}, headers=headers, status=201)


class DefaultPUT(Service):
    pass


class DefaultPATCH(Service):
    async def __call__(self):
        deserializer = queryMultiAdapter((self.context, self.request),
                                         IDeserializeFromJson)
        if deserializer is None:
            return ErrorResponse(
                'DeserializationError',
                'Cannot deserialize type {}'.format(obj.portal_type),
                status=501)

        try:
            deserializer()
        except DeserializationError as e:
            return ErrorResponse(
                'DeserializationError',
                str(e),
                status=400)

        return Response(response={}, status=204)


class SharingPOST(Service):
    pass


class DefaultDELETE(Service):

    async def __call__(self):
        content_id = self.context.id
        del self.context.__parent__[content_id]


class DefaultOPTIONS(Service):
    """Preflight view for Cors support on DX content."""

    def getRequestMethod(self):
        """Get the requested method."""
        return self.request.headers.get(
            'Access-Control-Request-Method', None)

    async def preflight(self):
        """We need to check if there is cors enabled and is valid."""
        headers = {}

        if self.settings.enabled is False:
            return {}

        origin = self.request.headers.get('Origin', None)
        if not origin:
            raise HTTPNotFound(text='Origin this header is mandatory')

        requested_method = self.getRequestMethod()
        if not requested_method:
            raise HTTPNotFound(
                text='Access-Control-Request-Method this header is mandatory')

        requested_headers = (
            self.request.headers.get('Access-Control-Request-Headers', ()))

        if requested_headers:
            requested_headers = map(str.strip, requested_headers.split(', '))

        requested_method = requested_method.upper()
        allowed_methods = self.settings.allow_methods
        if requested_method not in allowed_methods:
            raise HTTPMethodNotAllowed(
                requested_method, allowed_methods,
                text='Access-Control-Request-Method Method not allowed')

        supported_headers = self.settings.allow_headers
        if '*' not in supported_headers and requested_headers:
            supported_headers = [s.lower() for s in supported_headers]
            for h in requested_headers:
                if not h.lower() in supported_headers:
                    raise HTTPUnauthorized(
                        text='Access-Control-Request-Headers Header %s not allowed' % h)

        supported_headers = [] if supported_headers is None else supported_headers
        requested_headers = [] if requested_headers is None else requested_headers

        supported_headers = set(supported_headers) | set(requested_headers)

        headers['Access-Control-Allow-Headers'] = ','.join(
            supported_headers)
        headers['Access-Control-Allow-Methods'] = ','.join(
            self.settings.allow_methods)
        headers['Access-Control-Max-Age'] = str(self.settings.max_age)
        return headers

    async def render(self):
        """Need to be overwritten in case you implement OPTIONS."""
        return HTTPFound()

    async def apply_cors(self):
        """Second part of the cors function to validate."""
        headers = {}
        origin = self.request.headers.get('Origin', None)
        if origin:
            if not any([fnmatch.fnmatchcase(origin, o)
               for o in self.settings.allow_origin]):
                raise HTTPUnauthorized('Origin %s not allowed' % origin)
            elif self.request.headers.get('Access-Control-Allow-Credentials', False):
                headers['Allow-Control-Allow-Origin', origin]
            else:
                if any([o == "*" for o in self.settings.allow_origin]):
                    headers['Allow-Control-Allow-Origin'] = '*'
                else:
                    headers['Allow-Control-Allow-Origin'] = origin
        if self.getRequestMethod() != 'OPTIONS':
            if self.settings.allow_credentials:
                headers['Access-Control-Allow-Credentials'] = True
            if len(self.settings.supported_headers):
                headers['Access-Control-Expose-Headers'] = \
                    ', '.join(self.settings.supported_headers)
        return headers

    async def __call__(self):
        """Apply CORS on the OPTIONS view."""
        self.settings = self.request.site_settings.forInterface(ICors)
        headers = await self.preflight()
        resp = await self.render()
        headers.update(await self.apply_cors())
        return ResponseWithHeaders(resp, headers)

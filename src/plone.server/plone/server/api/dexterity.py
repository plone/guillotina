# -*- coding: utf-8 -*-
from plone.jsonserializer.interfaces import ISerializeToJson
from plone.server.api.service import Service
from plone.server.registry import ICors
from plone.server.browser import get_physical_path
from zope.component import getMultiAdapter
from aiohttp.web_exceptions import HTTPNotFound
from aiohttp.web_exceptions import HTTPUnauthorized
from aiohttp.web_exceptions import HTTPFound
from plone.server.browser import ResponseWithHeaders
import fnmatch


class DefaultGET(Service):
    async def __call__(self):
        serializer = getMultiAdapter(
            (self.context, self.request),
            ISerializeToJson)
        return serializer()


class DefaultPOST(Service):
    async def __call__(self):
        serializer = getMultiAdapter(
            (self.context, self.request),
            ISerializeToJson)
        return serializer()


class DefaultPUT(Service):
    pass


class DefaultPATCH(Service):
    pass


class SharingPOST(Service):
    pass


class DefaultDELETE(Service):
    pass


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
            raise HTTPNotFound(
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

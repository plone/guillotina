# -*- coding: utf-8 -*-
from plone.jsonserializer.interfaces import ISerializeToJson
from plone.jsonserializer.interfaces import IDeserializeFromJson
from plone.server.api.service import Service
from plone.server.api.service import TraversableService
from plone.server.registry import ICors
from plone.server.browser import get_physical_path
from zope.component import getMultiAdapter
from plone.server.browser import Response
from plone.server.browser import ErrorResponse
from plone.server.browser import UnauthorizedResponse
from plone.server.interfaces import IAbsoluteURL
from plone.server.interfaces import IObjectComponent
from plone.server.utils import DefaultRootCors
from plone.server import _
import fnmatch
from zope.security import checkPermission
from zope.security.interfaces import Unauthorized
from plone.dexterity.utils import createContentInContainer
from zope.component import queryMultiAdapter
import traceback
from datetime import datetime
import logging
from random import randint
from plone.jsonserializer.exceptions import DeserializationError
from plone.server.utils import get_authenticated_user_id
from plone.server.utils import apply_cors
from zope.container.interfaces import INameChooser
from zope.event import notify
from plone.server.events import ObjectFinallyCreatedEvent
from plone.server.utils import iter_parents
from zope.securitypolicy.interfaces import IPrincipalRoleManager
from zope.securitypolicy.interfaces import IPrincipalPermissionMap
from zope.securitypolicy.interfaces import IPrincipalRoleMap
from zope.securitypolicy.interfaces import IRolePermissionMap


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
        data = await self.request.json()
        type_ = data.get('@type', None)
        id_ = data.get('id', None)
        title = data.get('title', None)

        if not type_:
            return ErrorResponse(
                'RequiredParam',
                _("Property '@type' is required"))

        # Generate a temporary id if the id is not given
        if not id_ and title:
            new_id = INameChooser(self.context).chooseName(title, object())
        elif not id_:
            now = datetime.now()
            new_id = '{}.{}.{}{:04d}'.format(
                type_.lower().replace(' ', '_'),
                now.strftime('%Y-%m-%d'),
                str(now.timestamp())[7:],
                randint(0, 9999))
        else:
            new_id = id_

        # It already exists
        if new_id in self.context:
            return ErrorResponse(
                'Conflict',
                _("Id already exists"))

        user = get_authenticated_user_id(self.request)
        # Create object
        try:
            obj = createContentInContainer(
                self.context, type_, id=new_id, creators=(user,),
                contributors=(user,))
        except ValueError as e:
            return ErrorResponse(
                'CreatingObject',
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

        # Local Roles assign owner as the creator user
        roleperm = IPrincipalRoleManager(obj)
        roleperm.assignRoleToPrincipal(
            'plone.Owner',
            user)

        notify(ObjectFinallyCreatedEvent(obj))

        absolute_url = queryMultiAdapter((obj, self.request), IAbsoluteURL)

        headers = {
            'Location': absolute_url()
        }
        return Response(response={'@id': new_id}, headers=headers, status=201)


class DefaultPUT(Service):
    pass


class DefaultPATCH(Service):
    async def __call__(self):
        data = await self.request.json()
        deserializer = queryMultiAdapter((self.context, self.request),
                                         IDeserializeFromJson)
        if deserializer is None:
            return ErrorResponse(
                'DeserializationError',
                'Cannot deserialize type {}'.format(obj.portal_type),
                status=501)

        try:
            deserializer(data)
        except DeserializationError as e:
            return ErrorResponse(
                'DeserializationError',
                str(e),
                status=400)

        return Response(response={}, status=204)


class SharingGET(Service):
    """ Return the list of permissions """

    async def __call__(self):
        roleperm = IRolePermissionMap(self.context)
        prinperm = IPrincipalPermissionMap(self.context)
        prinrole = IPrincipalRoleMap(self.context)
        result = {
            'local': {},
            'inherit': []
        }
        result['local']['role_permission'] = roleperm._byrow
        result['local']['principal_permission'] = prinperm._byrow
        result['local']['principal_role'] = prinrole._byrow
        for obj in iter_parents(self.context):
            roleperm = IRolePermissionMap(obj)
            prinperm = IPrincipalPermissionMap(obj)
            prinrole = IPrincipalRoleMap(obj)
            result['inherit'].append({
                '@id': IAbsoluteURL(obj, self.request)(),
                'role_permission': roleperm._byrow,
                'principal_permission': prinperm._byrow,
                'principal_role': prinrole._byrow,
            })
        return result


class SharingPOST(Service):
    pass


class DefaultDELETE(Service):

    async def __call__(self):
        content_id = self.context.id
        del self.context.__parent__[content_id]


class ComponentsGET(TraversableService):

    def publishTraverse(self, traverse):
        if len(traverse) == 1:
            # we want have the key of the registry
            self.value = queryMultiAdapter(
                (self.context, self.request),
                IObjectComponent, name=traverse[0])
            self.component_id = traverse[0]
        else:
            self.value = None
            self.component_id = None
        return self

    async def __call__(self):
        component = {
            'id': self.component_id,
            'data': {
                'items': self.value()
            }
        }
        return component


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
        return {}

    async def __call__(self):
        """Apply CORS on the OPTIONS view."""
        if hasattr(self.request, 'site_settings'):
            self.settings = self.request.site_settings.forInterface(ICors)
        else:
            # CORS method for non plone endpoints
            self.settings = DefaultRootCors()

        headers = await self.preflight()
        resp = await self.render()
        return Response(response=resp, headers=headers, status=200)

# -*- coding: utf-8 -*-
from aiohttp.web_exceptions import HTTPMethodNotAllowed
from aiohttp.web_exceptions import HTTPNotFound
from aiohttp.web_exceptions import HTTPUnauthorized
from dateutil.tz import tzlocal
from guillotina import _
from guillotina import app_settings
from guillotina import configure
from guillotina import security
from guillotina.api.service import Service
from guillotina.auth.role import local_roles
from guillotina.browser import ErrorResponse
from guillotina.browser import Response
from guillotina.component import getMultiAdapter
from guillotina.component import queryMultiAdapter
from guillotina.content import create_content_in_container
from guillotina.content import get_all_behavior_interfaces
from guillotina.db.utils import lock_object
from guillotina.event import notify
from guillotina.events import BeforeObjectRemovedEvent
from guillotina.events import ObjectAddedEvent
from guillotina.events import ObjectModifiedEvent
from guillotina.events import ObjectPermissionsModifiedEvent
from guillotina.events import ObjectPermissionsViewEvent
from guillotina.events import ObjectRemovedEvent
from guillotina.events import ObjectVisitedEvent
from guillotina.exceptions import ConflictIdOnContainer
from guillotina.exceptions import PreconditionFailed
from guillotina.interfaces import IAbsoluteURL
from guillotina.interfaces import IInteraction
from guillotina.interfaces import IPrincipalPermissionManager
from guillotina.interfaces import IPrincipalPermissionMap
from guillotina.interfaces import IPrincipalRoleManager
from guillotina.interfaces import IPrincipalRoleMap
from guillotina.interfaces import IResource
from guillotina.interfaces import IResourceDeserializeFromJson
from guillotina.interfaces import IResourceSerializeToJson
from guillotina.interfaces import IRolePermissionManager
from guillotina.interfaces import IRolePermissionMap
from guillotina.json.exceptions import DeserializationError
from guillotina.json.utils import convert_interfaces_to_schema
from guillotina.utils import get_authenticated_user_id
from guillotina.utils import iter_parents
from guillotina.utils import valid_id


_zone = tzlocal()


def get_content_json_schema_responses(content):
    return {
        "200": {
            "description": "Resource data",
            "schema": {
                "allOf": [
                    {"$ref": "#/definitions/ResourceFolder"},
                    {"properties": convert_interfaces_to_schema(
                        get_all_behavior_interfaces(content))}
                ]
            }
        }
    }


def patch_content_json_schema_parameters(content):
    return [{
        "name": "body",
        "in": "body",
        "schema": {
            "allOf": [
                {"$ref": "#/definitions/WritableResource"},
                {"properties": convert_interfaces_to_schema(
                    get_all_behavior_interfaces(content))}
            ]
        }
    }]


@configure.service(
    context=IResource, method='GET', permission='guillotina.ViewContent',
    summary="Retrieves serialization of resource",
    responses=get_content_json_schema_responses)
class DefaultGET(Service):
    async def __call__(self):
        serializer = getMultiAdapter(
            (self.context, self.request),
            IResourceSerializeToJson)
        result = await serializer()
        await notify(ObjectVisitedEvent(self.context))
        return result


@configure.service(
    context=IResource, method='POST', permission='guillotina.AddContent',
    summary='Add new resouce inside this container resource',
    parameters=[{
        "name": "body",
        "in": "body",
        "schema": {
            "$ref": "#/definitions/AddableResource"
        }
    }],
    responses={
        "200": {
            "description": "Resource data",
            "schema": {
                "$ref": "#/definitions/ResourceFolder"
            }
        }
    })
class DefaultPOST(Service):

    async def __call__(self):
        """To create a content."""
        data = await self.get_data()
        type_ = data.get('@type', None)
        id_ = data.get('id', None)
        behaviors = data.get('@behaviors', None)

        if '__acl__' in data:
            # we don't allow to change the permisions on this patch
            del data['__acl__']

        if not type_:
            return ErrorResponse(
                'RequiredParam',
                _("Property '@type' is required"))

        # Generate a temporary id if the id is not given
        if not id_:
            new_id = None
        else:
            if not valid_id(id_):
                return ErrorResponse('PreconditionFailed', str('Invalid id'),
                                     status=412)
            new_id = id_

        user = get_authenticated_user_id(self.request)

        # Create object
        try:
            obj = await create_content_in_container(
                self.context, type_, new_id, id=new_id, creators=(user,),
                contributors=(user,))
        except PreconditionFailed as e:
            return ErrorResponse(
                'PreconditionFailed',
                str(e),
                status=412)
        except ConflictIdOnContainer as e:
            return ErrorResponse(
                'ConflictId',
                str(e),
                status=409)
        except ValueError as e:
            return ErrorResponse(
                'CreatingObject',
                str(e),
                status=400)

        for behavior in behaviors or ():
            obj.add_behavior(behavior)

        # Update fields
        deserializer = queryMultiAdapter((obj, self.request),
                                         IResourceDeserializeFromJson)
        if deserializer is None:
            return ErrorResponse(
                'DeserializationError',
                'Cannot deserialize type {}'.format(obj.type_name),
                status=501)

        try:
            await deserializer(data, validate_all=True)
        except DeserializationError as e:
            return ErrorResponse(
                'DeserializationError',
                str(e),
                exc=e,
                status=400)

        # Local Roles assign owner as the creator user
        roleperm = IPrincipalRoleManager(obj)
        roleperm.assign_role_to_principal(
            'guillotina.Owner',
            user)

        await notify(ObjectAddedEvent(obj, self.context, obj.id, payload=data))

        absolute_url = queryMultiAdapter((obj, self.request), IAbsoluteURL)

        headers = {
            'Access-Control-Expose-Headers': 'Location',
            'Location': absolute_url()
        }

        serializer = queryMultiAdapter(
            (obj, self.request),
            IResourceSerializeToJson
        )
        response = await serializer()
        return Response(response=response, headers=headers, status=201)


@configure.service(
    context=IResource, method='PATCH', permission='guillotina.ModifyContent',
    summary='Modify the content of this resource',
    parameters=patch_content_json_schema_parameters,
    responses={
        "200": {
            "description": "Resource data",
            "schema": {
                "$ref": "#/definitions/Resource"
            }
        }
    })
class DefaultPATCH(Service):
    async def __call__(self):
        await lock_object(self.context)
        data = await self.get_data()
        behaviors = data.get('@behaviors', None)
        for behavior in behaviors or ():
            self.context.add_behavior(behavior)

        deserializer = queryMultiAdapter((self.context, self.request),
                                         IResourceDeserializeFromJson)
        if deserializer is None:
            return ErrorResponse(
                'DeserializationError',
                'Cannot deserialize type {}'.format(self.context.type_name),
                status=501)

        try:
            await deserializer(data)
        except DeserializationError as e:
            return ErrorResponse(
                'DeserializationError',
                str(e),
                status=400)

        await notify(ObjectModifiedEvent(self.context, data))

        return Response(response={}, status=204)


@configure.service(
    context=IResource, method='GET',
    permission='guillotina.SeePermissions', name='@sharing',
    summary='Get sharing settings for this resource',
    responses={
        "200": {
            "description": "All the sharing defined on this resource",
            "schema": {
                "$ref": "#/definitions/ResourceACL"
            }
        }
    })
async def sharing_get(context, request):
    roleperm = IRolePermissionMap(context)
    prinperm = IPrincipalPermissionMap(context)
    prinrole = IPrincipalRoleMap(context)
    result = {
        'local': {},
        'inherit': []
    }
    result['local']['roleperm'] = roleperm._bycol
    result['local']['prinperm'] = prinperm._bycol
    result['local']['prinrole'] = prinrole._bycol
    for obj in iter_parents(context):
        roleperm = IRolePermissionMap(obj, None)
        if roleperm is not None:
            prinperm = IPrincipalPermissionMap(obj)
            prinrole = IPrincipalRoleMap(obj)
            result['inherit'].append({
                '@id': IAbsoluteURL(obj, request)(),
                'roleperm': roleperm._bycol,
                'prinperm': prinperm._bycol,
                'prinrole': prinrole._bycol,
            })
    await notify(ObjectPermissionsViewEvent(context))
    return result


@configure.service(
    context=IResource, method='GET',
    permission='guillotina.SeePermissions', name='@all_permissions',
    summary='See all permission settings for this resource',
    responses={
        "200": {
            "description": "All the permissions defined on this resource",
            "schema": {
                "$ref": "#/definitions/AllPermissions"
            }
        }
    })
async def all_permissions(context, request):
    result = security.utils.settings_for_object(context)
    await notify(ObjectPermissionsViewEvent(context))
    return result


PermissionMap = {
    'prinrole': {
        'Allow': 'assign_role_to_principal',
        'Deny': 'remove_role_from_principal',
        'AllowSingle': 'assign_role_to_principal_no_inherit',
        'Unset': 'unset_role_for_principal'
    },
    'roleperm': {
        'Allow': 'grant_permission_to_role',
        'Deny': 'deny_permission_to_role',
        'AllowSingle': 'grant_permission_to_role_no_inherit',
        'Unset': 'unset_permission_from_role'
    },
    'prinperm': {
        'Allow': 'grant_permission_to_principal',
        'Deny': 'deny_permission_to_principal',
        'AllowSingle': 'grant_permission_to_principal_no_inherit',
        'Unset': 'unset_permission_for_principal'
    }
}


@configure.service(
    context=IResource, method='POST',
    permission='guillotina.ChangePermissions', name='@sharing',
    summary='Change permissions for a resource',
    parameters=[{
        "name": "body",
        "in": "body",
        "type": "object",
        "schema": {
            "$ref": "#/definitions/Permissions"
        }
    }],
    responses={
        "200": {
            "description": "Successuflly changed permission"
        }
    })
async def sharing_post(context, request):
    """Change permissions"""
    await lock_object(context)
    lroles = local_roles()
    data = await request.json()
    if 'prinrole' not in data and \
            'roleperm' not in data and \
            'prinperm' not in data:
        raise AttributeError('prinrole or roleperm or prinperm missing')

    # we need to check if we are changing any info
    changed = False

    for prinrole in data.get('prinrole') or []:
        setting = prinrole.get('setting')
        if setting not in PermissionMap['prinrole']:
            raise AttributeError('Invalid Type {}'.format(setting))
        manager = IPrincipalRoleManager(context)
        operation = PermissionMap['prinrole'][setting]
        func = getattr(manager, operation)
        if prinrole['role'] in lroles:
            changed = True
            func(prinrole['role'], prinrole['principal'])
        else:
            raise KeyError('No valid local role')

    for prinperm in data.get('prinperm') or []:
        setting = prinperm['setting']
        if setting not in PermissionMap['prinperm']:
            raise AttributeError('Invalid Type')
        manager = IPrincipalPermissionManager(context)
        operation = PermissionMap['prinperm'][setting]
        func = getattr(manager, operation)
        changed = True
        func(prinperm['permission'], prinperm['principal'])

    for roleperm in data.get('roleperm') or []:
        setting = roleperm['setting']
        if setting not in PermissionMap['roleperm']:
            raise AttributeError('Invalid Type')
        manager = IRolePermissionManager(context)
        operation = PermissionMap['roleperm'][setting]
        func = getattr(manager, operation)
        changed = True
        func(roleperm['permission'], roleperm['role'])

    if changed:
        context._p_register()  # make sure data is saved
        await notify(ObjectPermissionsModifiedEvent(context, data))


@configure.service(
    context=IResource, method='GET',
    permission='guillotina.AccessContent', name='@canido',
    parameters=[{
        "name": "permission",
        "in": "query",
        "required": True,
        "type": "string"
    }],
    responses={
        "200": {
            "description": "Successuflly changed permission"
        }
    })
async def can_i_do(context, request):
    if 'permission' not in request.query:
        raise TypeError('No permission param')
    permission = request.query['permission']
    return IInteraction(request).check_permission(permission, context)


@configure.service(
    context=IResource, method='DELETE', permission='guillotina.DeleteContent',
    summary='Delete resource',
    responses={
        "200": {
            "description": "Successuflly deleted resource"
        }
    })
class DefaultDELETE(Service):

    async def __call__(self):
        content_id = self.context.id
        parent = self.context.__parent__
        await notify(BeforeObjectRemovedEvent(self.context, parent, content_id))
        self.context._p_jar.delete(self.context)
        await notify(ObjectRemovedEvent(self.context, parent, content_id))


@configure.service(
    context=IResource, method='OPTIONS', permission='guillotina.AccessPreflight',
    summary='Get CORS information for resource')
class DefaultOPTIONS(Service):
    """Preflight view for Cors support on DX content."""

    def getRequestMethod(self):  # noqa
        """Get the requested method."""
        return self.request.headers.get(
            'Access-Control-Request-Method', None)

    async def preflight(self):
        """We need to check if there is cors enabled and is valid."""
        headers = {}

        if not app_settings['cors']:
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
        allowed_methods = app_settings['cors']['allow_methods']
        if requested_method not in allowed_methods:
            raise HTTPMethodNotAllowed(
                requested_method, allowed_methods,
                text='Access-Control-Request-Method Method not allowed')

        supported_headers = app_settings['cors']['allow_headers']
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
            app_settings['cors']['allow_methods'])
        headers['Access-Control-Max-Age'] = str(app_settings['cors']['max_age'])
        return headers

    async def render(self):
        """Need to be overwritten in case you implement OPTIONS."""
        return {}

    async def __call__(self):
        """Apply CORS on the OPTIONS view."""
        headers = await self.preflight()
        resp = await self.render()
        if isinstance(resp, Response):
            headers.update(resp.headers)
            resp.headers = headers
            return resp
        return Response(response=resp, headers=headers, status=200)

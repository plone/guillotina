from guillotina import configure
from guillotina import error_reasons
from guillotina import security
from guillotina._cache import FACTORY_CACHE
from guillotina._settings import app_settings
from guillotina.annotations import AnnotationData
from guillotina.api.service import Service
from guillotina.auth.role import local_roles
from guillotina.component import get_multi_adapter
from guillotina.component import get_utility
from guillotina.component import query_adapter
from guillotina.component import query_multi_adapter
from guillotina.content import create_content_in_container
from guillotina.content import get_all_behavior_interfaces
from guillotina.content import get_all_behaviors
from guillotina.event import notify
from guillotina.events import BeforeObjectMovedEvent
from guillotina.events import BeforeObjectRemovedEvent
from guillotina.events import ObjectAddedEvent
from guillotina.events import ObjectDuplicatedEvent
from guillotina.events import ObjectModifiedEvent
from guillotina.events import ObjectMovedEvent
from guillotina.events import ObjectPermissionsModifiedEvent
from guillotina.events import ObjectPermissionsViewEvent
from guillotina.events import ObjectRemovedEvent
from guillotina.events import ObjectVisitedEvent
from guillotina.exceptions import PreconditionFailed
from guillotina.i18n import default_message_factory as _
from guillotina.interfaces import IAbsoluteURL
from guillotina.interfaces import IAnnotations
from guillotina.interfaces import IAsyncContainer
from guillotina.interfaces import IConstrainTypes
from guillotina.interfaces import IFolder
from guillotina.interfaces import IGetOwner
from guillotina.interfaces import IIDGenerator
from guillotina.interfaces import IInteraction
from guillotina.interfaces import IPrincipalPermissionManager
from guillotina.interfaces import IPrincipalPermissionMap
from guillotina.interfaces import IPrincipalRoleManager
from guillotina.interfaces import IPrincipalRoleMap
from guillotina.interfaces import IResource
from guillotina.interfaces import IResourceDeserializeFromJson
from guillotina.interfaces import IResourceSerializeToJson
from guillotina.interfaces import IResourceSerializeToJsonSummary
from guillotina.interfaces import IResponse
from guillotina.interfaces import IRolePermissionManager
from guillotina.interfaces import IRolePermissionMap
from guillotina.json.utils import convert_interfaces_to_schema
from guillotina.profile import profilable
from guillotina.response import ErrorResponse
from guillotina.response import HTTPMethodNotAllowed
from guillotina.response import HTTPNotFound
from guillotina.response import HTTPUnauthorized
from guillotina.response import Response
from guillotina.transactions import get_transaction
from guillotina.utils import get_authenticated_user_id
from guillotina.utils import iter_parents
from guillotina.utils import navigate_to
from guillotina.utils import valid_id


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
    context=IResource, method='HEAD', permission='guillotina.ViewContent')
async def default_head(context, request):
    return {}


@configure.service(
    context=IResource, method='GET', permission='guillotina.ViewContent',
    summary="Retrieves serialization of resource",
    responses=get_content_json_schema_responses,
    parameters=[{
        "name": "include",
        "in": "query",
        "type": "string"
    }, {
        "name": "omit",
        "in": "query",
        "type": "string"
    }])
class DefaultGET(Service):
    @profilable
    async def __call__(self):
        serializer = get_multi_adapter(
            (self.context, self.request),
            IResourceSerializeToJson)
        include = omit = []
        if self.request.query.get('include'):
            include = self.request.query.get('include').split(',')
        if self.request.query.get('omit'):
            omit = self.request.query.get('omit').split(',')
        try:
            result = await serializer(include=include, omit=omit)
        except TypeError:
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

    @profilable
    async def __call__(self):
        """To create a content."""
        data = await self.get_data()
        type_ = data.get('@type', None)
        id_ = data.get('id', None)
        behaviors = data.get('@behaviors', None)

        if not type_:
            raise ErrorResponse(
                'RequiredParam',
                _("Property '@type' is required"),
                reason=error_reasons.REQUIRED_PARAM_MISSING,
                status=412)

        # Generate a temporary id if the id is not given
        new_id = None
        if not id_:
            generator = query_adapter(self.request, IIDGenerator)
            if generator is not None:
                new_id = generator(data)
        else:
            if not isinstance(id_, str) or not valid_id(id_):
                raise ErrorResponse(
                    'PreconditionFailed', str('Invalid id'),
                    status=412, reason=error_reasons.INVALID_ID)
            new_id = id_

        user = get_authenticated_user_id(self.request)

        # Create object
        try:
            obj = await create_content_in_container(
                self.context, type_, new_id, id=new_id, creators=(user,),
                contributors=(user,))
        except ValueError as e:
            return ErrorResponse(
                'CreatingObject',
                str(e),
                status=412)

        for behavior in behaviors or ():
            obj.add_behavior(behavior)

        # Update fields
        deserializer = query_multi_adapter((obj, self.request),
                                           IResourceDeserializeFromJson)
        if deserializer is None:
            return ErrorResponse(
                'DeserializationError',
                'Cannot deserialize type {}'.format(obj.type_name),
                status=412,
                reason=error_reasons.DESERIALIZATION_FAILED)

        await deserializer(data, validate_all=True, create=True)

        # Local Roles assign owner as the creator user
        get_owner = get_utility(IGetOwner)
        roleperm = IPrincipalRoleManager(obj)
        owner = await get_owner(obj, user)
        if owner is not None:
            roleperm.assign_role_to_principal('guillotina.Owner', owner)

        data['id'] = obj.id
        await notify(ObjectAddedEvent(obj, self.context, obj.id, payload=data))

        absolute_url = query_multi_adapter((obj, self.request), IAbsoluteURL)

        headers = {
            'Access-Control-Expose-Headers': 'Location',
            'Location': absolute_url()
        }

        serializer = query_multi_adapter(
            (obj, self.request),
            IResourceSerializeToJsonSummary
        )
        response = await serializer()
        return Response(content=response, status=201, headers=headers)


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
        data = await self.get_data()

        behaviors = data.get('@behaviors', None)
        for behavior in behaviors or ():
            self.context.add_behavior(behavior)

        deserializer = query_multi_adapter((self.context, self.request),
                                           IResourceDeserializeFromJson)
        if deserializer is None:
            raise ErrorResponse(
                'DeserializationError',
                'Cannot deserialize type {}'.format(self.context.type_name),
                status=412,
                reason=error_reasons.DESERIALIZATION_FAILED)

        await deserializer(data)

        await notify(ObjectModifiedEvent(self.context, payload=data))

        return Response(status=204)


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
        url_factory = query_multi_adapter((obj, request), IAbsoluteURL)
        if roleperm is not None and url_factory is not None:
            prinperm = IPrincipalPermissionMap(obj)
            prinrole = IPrincipalRoleMap(obj)
            result['inherit'].append({
                '@id': url_factory(),
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
            "description": "Successfully changed permission"
        }
    })
class SharingPOST(Service):
    async def __call__(self, changed=False):
        """Change permissions"""
        context = self.context
        request = self.request
        lroles = local_roles()
        data = await request.json()
        if 'prinrole' not in data and \
                'roleperm' not in data and \
                'prinperm' not in data:
            raise PreconditionFailed(
                self.context, 'prinrole or roleperm or prinperm missing')

        for prinrole in data.get('prinrole') or []:
            setting = prinrole.get('setting')
            if setting not in PermissionMap['prinrole']:
                raise PreconditionFailed(
                    self.context, 'Invalid Type {}'.format(setting))
            manager = IPrincipalRoleManager(context)
            operation = PermissionMap['prinrole'][setting]
            func = getattr(manager, operation)
            if prinrole['role'] in lroles:
                changed = True
                func(prinrole['role'], prinrole['principal'])
            else:
                raise PreconditionFailed(
                    self.context, 'No valid local role')

        for prinperm in data.get('prinperm') or []:
            setting = prinperm['setting']
            if setting not in PermissionMap['prinperm']:
                raise PreconditionFailed(
                    self.context, 'Invalid Type')
            manager = IPrincipalPermissionManager(context)
            operation = PermissionMap['prinperm'][setting]
            func = getattr(manager, operation)
            changed = True
            func(prinperm['permission'], prinperm['principal'])

        for roleperm in data.get('roleperm') or []:
            setting = roleperm['setting']
            if setting not in PermissionMap['roleperm']:
                raise PreconditionFailed(
                    self.context, 'Invalid Type')
            manager = IRolePermissionManager(context)
            operation = PermissionMap['roleperm'][setting]
            func = getattr(manager, operation)
            changed = True
            func(roleperm['permission'], roleperm['role'])

        if changed:
            context._p_register()  # make sure data is saved
            await notify(ObjectPermissionsModifiedEvent(context, data))


@configure.service(
    context=IResource, method='PUT',
    permission='guillotina.ChangePermissions', name='@sharing',
    summary='Replace permissions for a resource',
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
            "description": "Successfully replaced permissions"
        }
    })
class SharingPUT(SharingPOST):
    async def __call__(self):
        self.context.__acl__ = None
        return await super().__call__(True)


@configure.service(
    context=IResource, method='GET',
    permission='guillotina.AccessContent', name='@canido',
    summary="Check if user has permissions on context",
    parameters=[{
        "name": "permission",
        "in": "query",
        "required": True,
        "type": "string"
    }],
    responses={
        "200": {
            "description": "Successfully changed permission"
        }
    })
async def can_i_do(context, request):
    if 'permission' not in request.query and 'permissions' not in request.query:
        raise PreconditionFailed(context, 'No permission param')
    interaction = IInteraction(request)
    if 'permissions' in request.query:
        results = {}
        for perm in request.query['permissions'].split(','):
            results[perm] = interaction.check_permission(perm, context)
        return results
    else:
        return interaction.check_permission(request.query['permission'], context)


@configure.service(
    context=IResource, method='DELETE', permission='guillotina.DeleteContent',
    summary='Delete resource',
    responses={
        "200": {
            "description": "Successfully deleted resource"
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

        renderer = app_settings['cors_renderer'](self.request)
        settings = await renderer.get_settings()

        if not settings:
            return {}

        origin = self.request.headers.get('Origin', None)
        if not origin:
            raise HTTPNotFound(content={
                'message': 'Origin this header is mandatory'
            })

        requested_method = self.getRequestMethod()
        if not requested_method:
            raise HTTPNotFound(content={
                'text': 'Access-Control-Request-Method this header is mandatory'
            })

        requested_headers = (
            self.request.headers.get('Access-Control-Request-Headers', ()))

        if requested_headers:
            requested_headers = map(str.strip, requested_headers.split(', '))

        requested_method = requested_method.upper()
        allowed_methods = settings['allow_methods']
        if requested_method not in allowed_methods:
            raise HTTPMethodNotAllowed(
                requested_method, allowed_methods,
                content={
                    'message': 'Access-Control-Request-Method Method not allowed'
                })

        supported_headers = settings['allow_headers']
        if '*' not in supported_headers and requested_headers:
            supported_headers = [s.lower() for s in supported_headers]
            for h in requested_headers:
                if not h.lower() in supported_headers:
                    raise HTTPUnauthorized(content={
                        'text': 'Access-Control-Request-Headers Header %s not allowed' % h
                    })

        supported_headers = [] if supported_headers is None else supported_headers
        requested_headers = [] if requested_headers is None else requested_headers

        supported_headers = set(supported_headers) | set(requested_headers)

        headers['Access-Control-Allow-Headers'] = ','.join(supported_headers)
        headers['Access-Control-Allow-Methods'] = ','.join(settings['allow_methods'])
        headers['Access-Control-Max-Age'] = str(settings['max_age'])
        return headers

    async def render(self):
        """Need to be overwritten in case you implement OPTIONS."""
        return {}

    async def __call__(self):
        """Apply CORS on the OPTIONS view."""
        headers = await self.preflight()
        resp = await self.render()
        if IResponse.providedBy(resp):
            headers.update(resp.headers)
            resp.headers = headers
            return resp
        return Response(content=resp, headers=headers)


@configure.service(
    context=IResource, method='POST', name="@move",
    permission='guillotina.MoveContent',
    summary='Move resource',
    parameters=[{
        "name": "body",
        "in": "body",
        "type": "object",
        "schema": {
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "Absolute path to destination object from container",
                    "required": False
                },
                "new_id": {
                    "type": "string",
                    "description": "Optional new id to assign object",
                    "required": False
                }
            }
        }
    }],
    responses={
        "200": {
            "description": "Successfully moved resource"
        }
    })
async def move(context, request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    destination = data.get('destination')
    if destination is None:
        destination_ob = context.__parent__
    else:
        try:
            destination_ob = await navigate_to(request.container, destination)
        except KeyError:
            destination_ob = None

    if destination_ob is None:
        raise PreconditionFailed(context, 'Could not find destination object')
    old_id = context.id
    if 'new_id' in data:
        new_id = data['new_id']
        context.id = context.__name__ = new_id
    else:
        new_id = context.id

    security = IInteraction(request)
    if not security.check_permission('guillotina.AddContent', destination_ob):
        raise PreconditionFailed(
            context, 'You do not have permission to add content to the '
                     'destination object')

    if await destination_ob.async_contains(new_id):
        raise PreconditionFailed(
            context, f'Destination already has object with the id {new_id}')

    original_parent = context.__parent__

    txn = get_transaction(request)
    cache_keys = txn._cache.get_cache_keys(context, 'deleted')

    data['id'] = new_id
    await notify(
        BeforeObjectMovedEvent(context, original_parent, old_id, destination_ob,
                               new_id, payload=data))

    context.__parent__ = destination_ob
    context._p_register()

    await notify(
        ObjectMovedEvent(context, original_parent, old_id, destination_ob,
                         new_id, payload=data))

    cache_keys += txn._cache.get_cache_keys(context, 'added')
    await txn._cache.delete_all(cache_keys)

    absolute_url = query_multi_adapter((context, request), IAbsoluteURL)
    return {
        '@url': absolute_url()
    }


@configure.service(
    context=IResource, method='POST', name="@duplicate",
    permission='guillotina.DuplicateContent',
    summary='Duplicate resource',
    parameters=[{
        "name": "body",
        "in": "body",
        "type": "object",
        "schema": {
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "Absolute path to destination object from container",
                    "required": False
                },
                "new_id": {
                    "type": "string",
                    "description": "Optional new id to assign object",
                    "required": False
                }
            }
        }
    }],
    responses={
        "200": {
            "description": "Successfully duplicated object"
        }
    })
async def duplicate(context, request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    destination = data.get('destination')
    if destination is not None:
        destination_ob = await navigate_to(request.container, destination)
        if destination_ob is None:
            raise PreconditionFailed(
                context, 'Could not find destination object',)
    else:
        destination_ob = context.__parent__

    security = IInteraction(request)
    if not security.check_permission('guillotina.AddContent', destination_ob):
        raise PreconditionFailed(
            context, 'You do not have permission to add content to '
                     'the destination object',)

    if 'new_id' in data:
        new_id = data['new_id']
        if await destination_ob.async_contains(new_id):
            raise PreconditionFailed(
                context, f'Destination already has object with the id {new_id}')
    else:
        count = 1
        new_id = f'{context.id}-duplicate-{count}'
        while await destination_ob.async_contains(new_id):
            count += 1
            new_id = f'{context.id}-duplicate-{count}'

    new_obj = await create_content_in_container(
        destination_ob, context.type_name, new_id, id=new_id,
        creators=context.creators, contributors=context.contributors)

    for key in context.__dict__.keys():
        if key.startswith('__') or key.startswith('_BaseObject'):
            continue
        if key in ('id',):
            continue
        new_obj.__dict__[key] = context.__dict__[key]
    new_obj.__acl__ = context.__acl__
    for behavior in context.__behaviors__:
        new_obj.add_behavior(behavior)

    # need to copy annotation data as well...
    # load all annotations for context
    [b for b in await get_all_behaviors(context, load=True)]
    annotations_container = IAnnotations(new_obj)
    for anno_id, anno_data in context.__gannotations__.items():
        new_anno_data = AnnotationData()
        for key, value in anno_data.items():
            new_anno_data[key] = value
        await annotations_container.async_set(anno_id, new_anno_data)

    data['id'] = new_id
    await notify(
        ObjectDuplicatedEvent(new_obj, context, destination_ob, new_id, payload=data))

    get = DefaultGET(new_obj, request)
    return await get()


@configure.service(
    context=IFolder, method='GET', name="@ids",
    permission='guillotina.ViewContent',
    summary='Return a list of ids in the resource',
    responses={
        "200": {
            "description": "Successfully returned list of ids"
        }
    })
async def ids(context, request):
    return await context.async_keys()


@configure.service(
    context=IFolder, method='GET', name="@items",
    permission='guillotina.ViewContent',
    summary='Paginated list of sub objects',
    parameters=[{
        "name": "include",
        "in": "query",
        "type": "string"
    }, {
        "name": "omit",
        "in": "query",
        "type": "string"
    }, {
        "name": "page_size",
        "in": "query",
        "type": "number",
        "default": 20
    }, {
        "name": "page",
        "in": "query",
        "type": "number",
        "default": 1
    }],
    responses={
        "200": {
            "description": "Successfully returned response object"
        }
    })
async def items(context, request):

    try:
        page_size = int(request.query['page_size'])
    except Exception:
        page_size = 20
    try:
        page = int(request.query['page'])
    except Exception:
        page = 1

    txn = get_transaction(request)

    include = omit = []
    if request.query.get('include'):
        include = request.query.get('include').split(',')
    if request.query.get('omit'):
        omit = request.query.get('omit').split(',')

    security = IInteraction(request)

    results = []
    for key in await txn.get_page_of_keys(context._p_oid, page=page, page_size=page_size):
        ob = await context.async_get(key)
        if not security.check_permission('guillotina.ViewContent', ob):
            continue
        serializer = get_multi_adapter(
            (ob, request),
            IResourceSerializeToJson)
        try:
            results.append(await serializer(include=include, omit=omit))
        except TypeError:
            results.append(await serializer())

    return {
        'items': results,
        'total': await context.async_len(),
        'page': page,
        'page_size': page_size
    }


@configure.service(
    context=IAsyncContainer, method='GET', name="@addable-types",
    permission='guillotina.AddContent',
    summary='Return a list of type names that can be added to container',
    responses={
        "200": {
            "description": "Successfully returned list of type names"
        }
    })
async def addable_types(context, request):
    constrains = IConstrainTypes(context, None)
    types = constrains and constrains.get_allowed_types()
    if types is None:
        types = []
        for type_name in FACTORY_CACHE:
            types.append(type_name)
    return types


@configure.service(
    method='GET', name="@invalidate-cache",
    permission='guillotina.ModifyContent',
    summary='Invalidate cache of object',
    responses={
        "200": {
            "description": "Successfully invalidated"
        }
    })
async def invalidate_cache(context, request):
    txn = get_transaction(request)
    cache_keys = txn._cache.get_cache_keys(context)
    await txn._cache.delete_all(cache_keys)

from guillotina import configure
from guillotina import content
from guillotina import error_reasons
from guillotina import security
from guillotina._cache import FACTORY_CACHE
from guillotina._settings import app_settings
from guillotina.api.service import Service
from guillotina.component import get_adapter
from guillotina.component import get_multi_adapter
from guillotina.component import get_utility
from guillotina.component import query_adapter
from guillotina.component import query_multi_adapter
from guillotina.content import create_content_in_container
from guillotina.content import get_all_behavior_interfaces
from guillotina.content import get_all_behaviors
from guillotina.content import get_cached_factory
from guillotina.directives import merged_tagged_value_dict
from guillotina.directives import read_permission
from guillotina.event import notify
from guillotina.events import BeforeObjectModifiedEvent
from guillotina.events import BeforeObjectRemovedEvent
from guillotina.events import ObjectAddedEvent
from guillotina.events import ObjectModifiedEvent
from guillotina.events import ObjectPermissionsViewEvent
from guillotina.events import ObjectRemovedEvent
from guillotina.events import ObjectVisitedEvent
from guillotina.exceptions import ComponentLookupError
from guillotina.exceptions import PreconditionFailed
from guillotina.i18n import default_message_factory as _
from guillotina.interfaces import IAnnotations
from guillotina.interfaces import IAsyncContainer
from guillotina.interfaces import IConstrainTypes
from guillotina.interfaces import IContainer
from guillotina.interfaces import IFieldValueRenderer
from guillotina.interfaces import IFolder
from guillotina.interfaces import IGetOwner
from guillotina.interfaces import IIDChecker
from guillotina.interfaces import IIDGenerator
from guillotina.interfaces import IPrincipalPermissionMap
from guillotina.interfaces import IPrincipalRoleManager
from guillotina.interfaces import IPrincipalRoleMap
from guillotina.interfaces import IResource
from guillotina.interfaces import IResourceDeserializeFromJson
from guillotina.interfaces import IResourceSerializeToJson
from guillotina.interfaces import IResourceSerializeToJsonSummary
from guillotina.interfaces import IResponse
from guillotina.interfaces import IRolePermissionMap
from guillotina.json.utils import convert_interfaces_to_schema
from guillotina.profile import profilable
from guillotina.response import ErrorResponse
from guillotina.response import HTTPMethodNotAllowed
from guillotina.response import HTTPMovedPermanently
from guillotina.response import HTTPNotFound
from guillotina.response import HTTPPreconditionFailed
from guillotina.response import HTTPUnauthorized
from guillotina.response import Response
from guillotina.security.utils import apply_sharing
from guillotina.transactions import get_transaction
from guillotina.utils import get_authenticated_user_id
from guillotina.utils import get_behavior
from guillotina.utils import get_object_by_uid
from guillotina.utils import get_object_url
from guillotina.utils import get_security_policy
from guillotina.utils import iter_parents
from guillotina.utils import resolve_dotted_name


def get_content_json_schema_responses(content):
    return {
        "200": {
            "description": "Resource data",
            "content": {
                "application/json": {
                    "schema": {
                        "allOf": [
                            {"$ref": "#/components/schemas/ResourceFolder"},
                            {
                                "type": "object",
                                "properties": convert_interfaces_to_schema(
                                    get_all_behavior_interfaces(content)
                                ),
                            },
                        ]
                    }
                }
            },
        }
    }


def patch_content_json_schema_parameters(content):
    return {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "allOf": [
                        {"$ref": "#/components/schemas/WritableResource"},
                        {"properties": convert_interfaces_to_schema(get_all_behavior_interfaces(content))},
                    ],
                }
            }
        },
    }


@configure.service(context=IResource, method="HEAD", permission="guillotina.ViewContent")
async def default_head(context, request):
    return {}


@configure.service(
    context=IResource,
    method="GET",
    permission="guillotina.ViewContent",
    summary="Retrieves serialization of resource",
    responses=get_content_json_schema_responses,
    parameters=[
        {"name": "include", "in": "query", "required": True, "schema": {"type": "string"}},
        {"name": "omit", "in": "query", "required": True, "schema": {"type": "string"}},
    ],
)
class DefaultGET(Service):
    @profilable
    async def __call__(self):
        serializer = get_multi_adapter((self.context, self.request), IResourceSerializeToJson)
        include = omit = []
        if self.request.query.get("include"):
            include = self.request.query.get("include").split(",")
        if self.request.query.get("omit"):
            omit = self.request.query.get("omit").split(",")
        try:
            result = await serializer(include=include, omit=omit)
        except TypeError:
            result = await serializer()
        await notify(ObjectVisitedEvent(self.context))
        return result


@configure.service(
    context=IResource,
    method="POST",
    permission="guillotina.AddContent",
    summary="Add new resouce inside this container resource",
    requestBody={
        "required": True,
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AddableResource"}}},
    },
    responses={
        "200": {
            "description": "Resource data",
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ResourceFolder"}}},
        }
    },
)
class DefaultPOST(Service):
    @profilable
    async def __call__(self):
        """To create a content."""
        data = await self.get_data()
        type_ = data.get("@type", None)
        id_ = data.get("id", None)
        behaviors = data.get("@behaviors", None)

        if not type_:
            raise ErrorResponse(
                "RequiredParam",
                _("Property '@type' is required"),
                reason=error_reasons.REQUIRED_PARAM_MISSING,
                status=412,
            )

        id_checker = get_adapter(self.context, IIDChecker)
        # Generate a temporary id if the id is not given
        new_id = None
        if not id_:
            generator = query_adapter(self.request, IIDGenerator)
            if generator is not None:
                new_id = generator(data)
                if isinstance(new_id, str) and not await id_checker(new_id, type_):
                    raise ErrorResponse(
                        "PreconditionFailed",
                        "Invalid id: {}".format(new_id),
                        status=412,
                        reason=error_reasons.INVALID_ID,
                    )
        else:
            if not isinstance(id_, str) or not await id_checker(id_, type_):
                raise ErrorResponse(
                    "PreconditionFailed",
                    "Invalid id: {}".format(id_),
                    status=412,
                    reason=error_reasons.INVALID_ID,
                )
            new_id = id_

        user = get_authenticated_user_id()

        options = {"creators": (user,), "contributors": (user,)}
        if "uid" in data:
            options["__uuid__"] = data.pop("uid")

        # Create object
        try:
            obj = await create_content_in_container(self.context, type_, new_id, **options)
        except ValueError as e:
            return ErrorResponse("CreatingObject", str(e), status=412)

        for behavior in behaviors or ():
            obj.add_behavior(behavior)

        # Update fields
        deserializer = query_multi_adapter((obj, self.request), IResourceDeserializeFromJson)
        if deserializer is None:
            return ErrorResponse(
                "DeserializationError",
                "Cannot deserialize type {}".format(obj.type_name),
                status=412,
                reason=error_reasons.DESERIALIZATION_FAILED,
            )

        await deserializer(data, validate_all=True, create=True)

        # Local Roles assign owner as the creator user
        get_owner = get_utility(IGetOwner)
        roleperm = IPrincipalRoleManager(obj)
        owner = await get_owner(obj, user)
        if owner is not None:
            roleperm.assign_role_to_principal("guillotina.Owner", owner)

        data["id"] = obj.id
        await notify(ObjectAddedEvent(obj, self.context, obj.id, payload=data))

        headers = {"Access-Control-Expose-Headers": "Location", "Location": get_object_url(obj, self.request)}

        serializer = query_multi_adapter((obj, self.request), IResourceSerializeToJsonSummary)
        response = await serializer()
        return Response(content=response, status=201, headers=headers)


@configure.service(
    context=IResource,
    method="PATCH",
    permission="guillotina.ModifyContent",
    summary="Modify the content of this resource",
    requestBody=patch_content_json_schema_parameters,
    responses={
        "200": {
            "description": "Resource data",
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Resource"}}},
        }
    },
)
class DefaultPATCH(Service):
    async def __call__(self):
        data = await self.get_data()

        behaviors = data.get("@behaviors", None)
        for behavior in behaviors or ():
            try:
                self.context.add_behavior(behavior)
            except (TypeError, ComponentLookupError):
                return HTTPPreconditionFailed(
                    content={"message": f"{behavior} is not a valid behavior", "behavior": behavior}
                )

        deserializer = query_multi_adapter((self.context, self.request), IResourceDeserializeFromJson)
        if deserializer is None:
            raise ErrorResponse(
                "DeserializationError",
                "Cannot deserialize type {}".format(self.context.type_name),
                status=412,
                reason=error_reasons.DESERIALIZATION_FAILED,
            )

        await notify(BeforeObjectModifiedEvent(self.context, payload=data))

        await deserializer(data)

        await notify(ObjectModifiedEvent(self.context, payload=data))

        return Response(status=204)


@configure.service(
    context=IResource,
    method="PUT",
    permission="guillotina.ModifyContent",
    summary="Replace the content of this resource",
    requestBody=patch_content_json_schema_parameters,
    responses={
        "200": {
            "description": "Resource data",
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Resource"}}},
        }
    },
)
class DefaultPUT(DefaultPATCH):
    async def __call__(self):
        """
        PUT means we're completely replacing the content
        so we need to delete data from existing behaviors
        and content schemas.
        Then do the regular patch serialization
        """
        annotations_container = IAnnotations(self.context)
        for schema, behavior in await get_all_behaviors(self.context, load=False):
            if hasattr(behavior, "__annotations_data_key__"):
                await annotations_container.async_del(behavior.__annotations_data_key__)
            try:
                behavior.data.clear()
                for local_prop in vars(type(behavior)):
                    if local_prop[0] == "_":
                        continue
                    if local_prop in self.context.__dict__:
                        del self.context.__dict__[local_prop]
            except AttributeError:
                pass
        self.context.__behaviors__ = frozenset({})

        factory = get_cached_factory(self.context.type_name)
        if factory.schema is not None:
            for name in factory.schema.names():
                if name in self.context.__dict__:
                    del self.context.__dict__[name]
        return await super().__call__()


@configure.service(
    context=IResource,
    method="GET",
    permission="guillotina.SeePermissions",
    name="@sharing",
    summary="Get sharing settings for this resource",
    responses={
        "200": {
            "description": "All the sharing defined on this resource",
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ResourceACL"}}},
        }
    },
)
async def sharing_get(context, request):
    roleperm = IRolePermissionMap(context)
    prinperm = IPrincipalPermissionMap(context)
    prinrole = IPrincipalRoleMap(context)
    result = {"local": {}, "inherit": []}
    result["local"]["roleperm"] = roleperm._bycol
    result["local"]["prinperm"] = prinperm._bycol
    result["local"]["prinrole"] = prinrole._bycol
    for obj in iter_parents(context):
        roleperm = IRolePermissionMap(obj, None)
        url = get_object_url(obj, request)
        if roleperm is not None and url is not None:
            prinperm = IPrincipalPermissionMap(obj)
            prinrole = IPrincipalRoleMap(obj)
            result["inherit"].append(
                {
                    "@id": url,
                    "roleperm": roleperm._bycol,
                    "prinperm": prinperm._bycol,
                    "prinrole": prinrole._bycol,
                }
            )
    await notify(ObjectPermissionsViewEvent(context))
    return result


@configure.service(
    context=IResource,
    method="GET",
    permission="guillotina.SeePermissions",
    name="@all_permissions",
    summary="See all permission settings for this resource",
    responses={
        "200": {
            "description": "All the permissions defined on this resource",
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AllPermissions"}}},
        }
    },
)
async def all_permissions(context, request):
    result = security.utils.settings_for_object(context)
    await notify(ObjectPermissionsViewEvent(context))
    return result


@configure.service(
    context=IResource,
    method="POST",
    permission="guillotina.ChangePermissions",
    name="@sharing",
    summary="Change permissions for a resource",
    validate=True,
    requestBody={
        "required": True,
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Permissions"}}},
    },
    responses={"200": {"description": "Successfully changed permission"}},
)
class SharingPOST(Service):
    async def __call__(self, changed=False):
        """Change permissions"""
        context = self.context
        request = self.request
        data = await request.json()
        if (
            "prinrole" not in data
            and "roleperm" not in data
            and "prinperm" not in data
            and "perminhe" not in data
        ):
            raise PreconditionFailed(self.context, "prinrole or roleperm or prinperm missing")
        return await apply_sharing(context, data)


@configure.service(
    context=IResource,
    method="PUT",
    permission="guillotina.ChangePermissions",
    name="@sharing",
    summary="Replace permissions for a resource",
    validate=True,
    requestBody={
        "required": True,
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Permissions"}}},
    },
    responses={"200": {"description": "Successfully replaced permissions"}},
)
class SharingPUT(SharingPOST):
    async def __call__(self):
        self.context.__acl__ = None
        return await super().__call__(True)


@configure.service(
    context=IResource,
    method="GET",
    permission="guillotina.AccessContent",
    name="@canido",
    summary="Check if user has permissions on context",
    parameters=[{"name": "permission", "in": "query", "required": True, "schema": {"type": "string"}}],
    responses={"200": {"description": "Successfully changed permission"}},
)
async def can_i_do(context, request):
    if "permission" not in request.query and "permissions" not in request.query:
        raise PreconditionFailed(context, "No permission param")
    policy = get_security_policy()
    if "permissions" in request.query:
        results = {}
        for perm in request.query["permissions"].split(","):
            results[perm] = policy.check_permission(perm, context)
        return results
    else:
        return policy.check_permission(request.query["permission"], context)


@configure.service(
    context=IResource,
    method="DELETE",
    permission="guillotina.DeleteContent",
    summary="Delete resource",
    responses={"200": {"description": "Successfully deleted resource"}},
)
class DefaultDELETE(Service):
    async def __call__(self):
        content_id = self.context.id
        parent = self.context.__parent__
        await notify(BeforeObjectRemovedEvent(self.context, parent, content_id))
        self.context.__txn__.delete(self.context)
        await notify(ObjectRemovedEvent(self.context, parent, content_id))


@configure.service(
    context=IResource,
    method="OPTIONS",
    permission="guillotina.AccessPreflight",
    summary="Get CORS information for resource",
)
class DefaultOPTIONS(Service):
    """Preflight view for Cors support on DX content."""

    def getRequestMethod(self):  # noqa
        """Get the requested method."""
        return self.request.headers.get("Access-Control-Request-Method", None)

    async def preflight(self):
        """We need to check if there is cors enabled and is valid."""
        headers = {}

        renderer = app_settings["cors_renderer"](self.request)
        settings = await renderer.get_settings()

        if not settings:
            return {}

        origin = self.request.headers.get("Origin", None)
        if not origin:
            raise HTTPNotFound(content={"message": "Origin this header is mandatory"})

        requested_method = self.getRequestMethod()
        if not requested_method:
            raise HTTPNotFound(content={"text": "Access-Control-Request-Method this header is mandatory"})

        requested_headers = self.request.headers.get("Access-Control-Request-Headers", ())

        if requested_headers:
            requested_headers = map(str.strip, requested_headers.split(", "))

        requested_method = requested_method.upper()
        allowed_methods = settings["allow_methods"]
        if requested_method not in allowed_methods:
            raise HTTPMethodNotAllowed(
                requested_method,
                allowed_methods,
                content={"message": "Access-Control-Request-Method Method not allowed"},
            )

        supported_headers = settings["allow_headers"]
        if "*" not in supported_headers and requested_headers:
            supported_headers = [s.lower() for s in supported_headers]
            for h in requested_headers:
                if not h.lower() in supported_headers:
                    raise HTTPUnauthorized(
                        content={"text": "Access-Control-Request-Headers Header %s not allowed" % h}
                    )

        supported_headers = [] if supported_headers is None else supported_headers
        requested_headers = [] if requested_headers is None else requested_headers

        supported_headers = set(supported_headers) | set(requested_headers)

        headers["Access-Control-Allow-Headers"] = ",".join(supported_headers)
        headers["Access-Control-Allow-Methods"] = ",".join(settings["allow_methods"])
        headers["Access-Control-Max-Age"] = str(settings["max_age"])
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
    context=IResource,
    method="POST",
    name="@move",
    permission="guillotina.MoveContent",
    summary="Move resource",
    requestBody={
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "properties": {
                        "destination": {
                            "type": "string",
                            "description": "Absolute path to destination object from container or destination uid",
                        },
                        "new_id": {"type": "string", "description": "Optional new id to assign object"},
                    },
                    "additionalProperties": False,
                }
            }
        },
    },
    responses={"200": {"description": "Successfully moved resource"}},
)
async def move(context, request):
    try:
        data = await request.json()
    except Exception:
        data = {}

    try:
        await content.move(
            context, destination=data.get("destination"), new_id=data.get("new_id"), check_permission=True
        )
    except TypeError:
        raise ErrorResponse(
            "RequiredParam", _("Invalid params"), reason=error_reasons.REQUIRED_PARAM_MISSING, status=412
        )

    return {"@url": get_object_url(context, request)}


@configure.service(
    context=IResource,
    method="POST",
    name="@duplicate",
    permission="guillotina.DuplicateContent",
    summary="Duplicate resource",
    requestBody={
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "properties": {
                        "destination": {
                            "type": "string",
                            "description": "Absolute path to destination object from container or destination uid",
                        },
                        "new_id": {"type": "string", "description": "Optional new id to assign object"},
                        "reset_acl": {
                            "type": "boolean",
                            "description": "Remove users and roles from acl, except for the request user",
                            "default": False,
                        },
                    },
                    "additionalProperties": False,
                }
            }
        },
    },
    responses={"200": {"description": "Successfully duplicated object"}},
)
async def duplicate(context, request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    try:
        new_obj = await content.duplicate(
            context,
            destination=data.get("destination"),
            new_id=data.get("new_id"),
            check_permission=True,
            reset_acl=data.get("reset_acl", False),
        )
    except TypeError:
        raise ErrorResponse(
            "RequiredParam", _("Invalid params"), reason=error_reasons.REQUIRED_PARAM_MISSING, status=412
        )

    get = DefaultGET(new_obj, request)
    return await get()


@configure.service(
    context=IFolder,
    method="GET",
    name="@ids",
    permission="guillotina.Manage",
    summary="Return a list of ids in the resource",
    responses={"200": {"description": "Successfully returned list of ids"}},
)
async def ids(context, request):
    return await context.async_keys()


@configure.service(
    context=IFolder,
    method="GET",
    name="@items",
    permission="guillotina.Manage",
    summary="Paginated list of sub objects",
    parameters=[
        {"name": "include", "in": "query", "required": False, "schema": {"type": "string"}},
        {"name": "omit", "in": "query", "required": False, "schema": {"type": "string"}},
        {"name": "page_size", "in": "query", "required": False, "schema": {"type": "number"}},
        {"name": "page", "in": "query", "required": False, "schema": {"type": "number"}},
    ],
    responses={"200": {"description": "Successfully returned response object"}},
)
async def items(context, request):

    try:
        page_size = int(request.query["page_size"])
    except Exception:
        page_size = 20
    try:
        page = int(request.query["page"])
    except Exception:
        page = 1

    txn = get_transaction()

    include = omit = []
    if request.query.get("include"):
        include = request.query.get("include").split(",")
    if request.query.get("omit"):
        omit = request.query.get("omit").split(",")

    results = []
    for key in await txn.get_page_of_keys(context.__uuid__, page=page, page_size=page_size):
        ob = await context.async_get(key)
        serializer = get_multi_adapter((ob, request), IResourceSerializeToJson)
        try:
            results.append(await serializer(include=include, omit=omit))
        except TypeError:
            results.append(await serializer())

    return {"items": results, "total": await context.async_len(), "page": page, "page_size": page_size}


@configure.service(
    context=IAsyncContainer,
    method="GET",
    name="@addable-types",
    permission="guillotina.AddContent",
    summary="Return a list of type names that can be added to container",
    responses={"200": {"description": "Successfully returned list of type names"}},
)
async def addable_types(context, request):
    constrains = IConstrainTypes(context, None)
    types = constrains and constrains.get_allowed_types()
    if types is None:
        types = []
        for type_name in FACTORY_CACHE:
            types.append(type_name)
    app_settings["container_types"]
    types = [item for item in types if item not in app_settings["container_types"]]
    return types


@configure.service(
    method="GET",
    name="@invalidate-cache",
    permission="guillotina.ModifyContent",
    summary="Invalidate cache of object",
    responses={"200": {"description": "Successfully invalidated"}},
)
async def invalidate_cache(context, request):
    txn = get_transaction()
    cache_keys = txn._cache.get_cache_keys(context)
    await txn._cache.delete_all(cache_keys)


@configure.service(
    method="GET",
    name="@resolveuid/{uid}",
    context=IContainer,
    permission="guillotina.AccessContent",
    summary="Get content by UID",
    parameters=[{"in": "path", "name": "uid", "required": True, "schema": {"type": "string"}}],
    responses={"200": {"description": "Successful"}},
)
async def resolve_uid(context, request):
    uid = request.matchdict["uid"]
    try:
        ob = await get_object_by_uid(uid)
    except KeyError:
        return HTTPNotFound(content={"reason": f"Could not find uid: {uid}"})
    policy = get_security_policy()
    if policy.check_permission("guillotina.AccessContent", ob):
        return HTTPMovedPermanently(get_object_url(ob, request))
    else:
        # if a user doesn't have access to it, they shouldn't know anything about it
        return HTTPNotFound(content={"reason": f"Could not find uid: {uid}"})


@configure.service(
    context=IResource,
    method="GET",
    permission="guillotina.ViewContent",
    name="@fieldvalue/{dotted_name}",
    summary="Get field value",
)
async def get_field_value(context, request):
    field_name = request.matchdict["dotted_name"]

    if "." in field_name:
        # behavior field lookup
        iface_dotted = ".".join(field_name.split(".")[:-1])
        field_name = field_name.split(".")[-1]

        try:
            schema = resolve_dotted_name(iface_dotted)
        except ModuleNotFoundError:
            return HTTPNotFound(content={"reason": f"Could resolve: {iface_dotted}"})
        try:
            field = schema[field_name]
        except KeyError:
            return HTTPNotFound(content={"reason": f"No field: {field_name}"})

        try:
            behavior = await get_behavior(context, schema)
        except AttributeError:
            return HTTPNotFound(content={"reason": f"Could not load behavior: {iface_dotted}"})
        if behavior is None:
            return HTTPNotFound(content={"reason": f"Not valid behavior: {iface_dotted}"})
        field = field.bind(behavior)
        field_context = behavior
    else:
        # main object field
        factory = get_cached_factory(context.type_name)
        schema = factory.schema
        try:
            field = schema[field_name]
        except KeyError:
            return HTTPNotFound(content={"reason": f"No field: {field_name}"})
        field = field.bind(context)
        field_context = context

    # check permission
    read_permissions = merged_tagged_value_dict(schema, read_permission.key)
    serializer = get_multi_adapter((context, request), IResourceSerializeToJson)

    if not serializer.check_permission(read_permissions.get(field_name)):
        return HTTPUnauthorized(content={"reason": "You are not authorized to render this field"})

    field_renderer = query_multi_adapter((context, request, field), IFieldValueRenderer)
    if field_renderer is None:
        return await serializer.serialize_field(field_context, field)
    else:
        return await field_renderer()

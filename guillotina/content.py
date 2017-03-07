# -*- coding: utf-8 -*-
from copy import deepcopy
from datetime import datetime
from dateutil.tz import tzlocal
from guillotina import BEHAVIOR_CACHE
from guillotina import configure
from guillotina import FACTORY_CACHE
from guillotina import PERMISSIONS_CACHE
from guillotina import SCHEMA_CACHE
from guillotina.auth.users import ANONYMOUS_USER_ID
from guillotina.auth.users import ROOT_USER_ID
from guillotina.behaviors import applyMarkers
from guillotina.browser import get_physical_path
from guillotina.events import BeforeObjectAddedEvent
from guillotina.events import notify
from guillotina.exceptions import ConflictIdOnContainer
from guillotina.exceptions import NoPermissionToAdd
from guillotina.exceptions import NotAllowedContentType
from guillotina.interfaces import DEFAULT_ADD_PERMISSION
from guillotina.interfaces import IAddons
from guillotina.interfaces import IBehavior
from guillotina.interfaces import IBehaviorAssignable
from guillotina.interfaces import IConstrainTypes
from guillotina.interfaces import IContainer
from guillotina.interfaces import IInteraction
from guillotina.interfaces import IItem
from guillotina.interfaces import ILayers
from guillotina.interfaces import IPermission
from guillotina.interfaces import IPrincipalPermissionManager
from guillotina.interfaces import IPrincipalRoleManager
from guillotina.interfaces import IResource
from guillotina.interfaces import IResourceFactory
from guillotina.interfaces import ISite
from guillotina.interfaces import IStaticDirectory
from guillotina.interfaces import IStaticFile
from guillotina.security.security_code import PrincipalPermissionManager
from guillotina.utils import apply_coroutine
from guillotina.utils import get_current_request
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.component import getUtilitiesFor
from zope.component import getUtility
from zope.component import queryUtility
from zope.component.factory import Factory
from zope.interface import alsoProvides
from zope.interface import implementer
from zope.interface import Interface
from zope.interface import noLongerProvides
from guillotina.schema.interfaces import IContextAwareDefaultFactory

import guillotina.db.orm.base
import pathlib
import uuid


_zone = tzlocal()
_marker = object()


@implementer(IResourceFactory)
class ResourceFactory(Factory):
    portal_type = None
    schema = None
    behaviors = None
    add_permission = None

    def __init__(self, klass, title='', description='',
                 portal_type='', schema=None, behaviors=None,
                 add_permission=DEFAULT_ADD_PERMISSION,
                 allowed_types=None):
        super(ResourceFactory, self).__init__(
            klass, title, description,
            tuple(filter(bool, [schema] + list(behaviors) or list())))
        self.portal_type = portal_type
        self.schema = schema or Interface
        self.behaviors = behaviors or ()
        self.add_permission = add_permission
        self.allowed_types = allowed_types

    def __call__(self, id, *args, **kw):
        obj = super(ResourceFactory, self).__call__(*args, **kw)
        obj.portal_type = self.portal_type
        now = datetime.now(tz=_zone)
        obj.creation_date = now
        obj.modification_date = now
        obj.uuid = uuid.uuid4().hex
        if id is None:
            obj.id = obj.uuid
        else:
            obj.id = id
        applyMarkers(obj, None)
        return obj

    def getInterfaces(self):
        spec = super(ResourceFactory, self).getInterfaces()
        spec.__name__ = self.portal_type
        return spec

    def __repr__(self):
        return '<{0:s} for {1:s}>'.format(self.__class__.__name__,
                                          self.portal_type)


def load_cached_schema():
    for x in getUtilitiesFor(IResourceFactory):
        factory = x[1]
        if factory.portal_type not in SCHEMA_CACHE:
            behaviors_registrations = []
            for iface in factory.behaviors or ():
                if Interface.providedBy(iface):
                    name = iface.__identifier__
                else:
                    name = iface
                behaviors_registrations.append(getUtility(IBehavior, name=name))
            SCHEMA_CACHE[factory.portal_type] = {
                'behaviors': behaviors_registrations,
                'schema': factory.schema
            }
    for iface, utility in getUtilitiesFor(IBehavior):
        if isinstance(iface, str):
            name = iface
        elif Interface.providedBy(iface):
            name = iface.__identifier__
        if name not in BEHAVIOR_CACHE:
            BEHAVIOR_CACHE[name] = utility.interface


def get_cached_factory(portal_type):
    if portal_type in FACTORY_CACHE:
        factory = FACTORY_CACHE[portal_type]
    else:
        factory = getUtility(IResourceFactory, portal_type)
        FACTORY_CACHE[portal_type] = factory
    return factory


def iter_schemata_for_type(portal_type):
    factory = get_cached_factory(portal_type)
    if factory.schema is not None:
        yield factory.schema
    for schema in factory.behaviors or ():
        yield schema


def iter_schemata(obj):
    portal_type = IResource(obj).portal_type
    for schema in iter_schemata_for_type(portal_type):
        yield schema
    for schema in obj.__behaviors_schemas__:
        yield schema


async def create_content(type_, **kw):
    """Utility to create a content.

    This method should not be used to add content, just internally.
    """
    factory = get_cached_factory(type_)
    if 'id' in kw:
        id_ = kw['id']
    else:
        id_ = None

    # We create the object with at least the ID
    obj = factory(id=id_)
    for key, value in kw.items():
        setattr(obj, key, value)
    return obj


async def create_content_in_container(container, type_, id_, request=None, **kw):
    """Utility to create a content.

    This method is the one to use to create content.
    id_ can be None
    """
    factory = get_cached_factory(type_)

    if factory.add_permission:
        if factory.add_permission in PERMISSIONS_CACHE:
            permission = PERMISSIONS_CACHE[factory.add_permission]
        else:
            permission = queryUtility(IPermission, name=factory.add_permission)
            PERMISSIONS_CACHE[factory.add_permission] = permission

        if request is None:
            request = get_current_request()

        if permission is not None and \
                not IInteraction(request).check_permission(permission.id, container):
            raise NoPermissionToAdd(str(container), type_)

    constrains = IConstrainTypes(container, None)
    if constrains is not None:
        if not constrains.is_type_allowed(type_):
            raise NotAllowedContentType(str(container), type_)

    # We create the object with at least the ID
    obj = factory(id=id_)
    obj.__parent__ = container
    for key, value in kw.items():
        setattr(obj, key, value)

    if request is None or 'OVERWRITE' not in request.headers:
        value = await apply_coroutine(container.__contains__, obj.id)
        if value:
            raise ConflictIdOnContainer(str(container), obj.id)

    await notify(BeforeObjectAddedEvent(obj, container, id_))
    await apply_coroutine(container.__setitem__, obj.id, obj)
    return obj


@configure.adapter(for_=IResource, provides=IBehaviorAssignable)
class BehaviorAssignable(object):
    """Support guillotina.behaviors behaviors stored on the CACHE
    """

    def __init__(self, context):
        self.context = context

    def supports(self, behavior_interface):
        """We support all behaviors that accomplish the for_."""
        return True

    def enumerate_behaviors(self):
        for behavior in SCHEMA_CACHE[self.context.portal_type]['behaviors']:
            yield behavior
        for behavior in self.context.__behaviors__:
            yield BEHAVIOR_CACHE[behavior]


def _default_from_schema(context, schema, fieldname):
    """helper to lookup default value of a field
    """
    if schema is None:
        return _marker
    field = schema.get(fieldname, None)
    if field is None:
        return _marker
    if IContextAwareDefaultFactory.providedBy(
            getattr(field, 'defaultFactory', None)
    ):
        bound = field.bind(context)
        return deepcopy(bound.default)
    else:
        return deepcopy(field.default)
    return _marker


@implementer(IResource, IAttributeAnnotatable)
class Resource(guillotina.db.orm.base.BaseObject):

    __name__ = None
    __parent__ = None
    __behaviors__ = frozenset({})
    __acl__ = None

    portal_type = None
    uuid = None
    creation_date = None
    modification_date = None
    title = None

    def __init__(self, id=None):
        if id is not None:
            self.__name__ = id
        super(Resource, self).__init__()

    def __repr__(self):
        path = '/'.join(get_physical_path(self))
        return "< {type} at {path} by {mem} >".format(
            type=self.portal_type,
            path=path,
            mem=id(self))

    @property
    def acl(self):
        if self.__acl__ is None:
            return dict({})
        return self.__acl__

    def set_id(self, id_):
        if id_ is not None:
            self.__name__ = id_

    def get_id(self):
        return self.__name__

    id = property(get_id, set_id)

    @property
    def __behaviors_schemas__(self):
        """Get the dynamic schemas."""
        for behavior in self.__behaviors__:
            yield BEHAVIOR_CACHE[behavior]

    def add_behavior(self, iface):
        """We need to apply the marker interface.

        value: Interface to add
        """
        if isinstance(iface, str):
            name = iface
        elif Interface.providedBy(iface):
            name = iface.__identifier__
        else:
            raise AttributeError('Cant identify Interface')
        behavior_registration = getUtility(IBehavior, name=name)
        if behavior_registration is not None and\
                behavior_registration.interface(self) is not None:
            # We can adapt so we can apply this dynamic behavior
            self.__behaviors__ |= {name}
            if behavior_registration.marker is not None:
                alsoProvides(self, behavior_registration.marker)

    def remove_behavior(self, iface):
        """We need to apply the marker interface.

        value: Interface to add
        """
        if isinstance(iface, str):
            name = iface
        elif Interface.providedBy(iface):
            name = iface.__identifier__
        behavior_registration = getUtility(IBehavior, name=name)
        if behavior_registration is not None and\
                behavior_registration.marker is not None:
            noLongerProvides(self, behavior_registration.marker)
        if iface in self.__behaviors__:
            self.__behaviors__ -= {name}

    def __getattr__(self, name):
        # python basics:  __getattr__ is only invoked if the attribute wasn't
        # found by __getattribute__
        #
        # optimization: sometimes we're asked for special attributes
        # such as __conform__ that we can disregard (because we
        # wouldn't be in here if the class had such an attribute
        # defined).
        # also handle special dynamic providedBy cache here.
        # also handle the get_current_request call
        if name.startswith('__') or name == '_v__providedBy__' or name == 'request':
            raise AttributeError(name)

        # attribute was not found; try to look it up in the schema and return
        # a default
        value = _default_from_schema(
            self,
            SCHEMA_CACHE.get(self.portal_type).get('schema'),
            name
        )
        if value is not _marker:
            return value
        raise AttributeError(name)


@configure.contenttype(
    portal_type="Item",
    schema=IItem,
    behaviors=["guillotina.behaviors.dublincore.IDublinCore"])
class Item(Resource):
    pass


@configure.contenttype(
    portal_type="Folder",
    schema=IContainer,
    behaviors=["guillotina.behaviors.dublincore.IDublinCore"])
class Folder(Resource):
    async def __contains__(self, key):
        return await self._p_jar.contains(self._p_oid, key)

    async def __setitem__(self, key, value):
        value.__parent__ = self
        value.__name__ = key
        if self._p_jar is not None:
            value._p_jar = self._p_jar
            self._p_jar.register(value)

    async def __getitem__(self, key):
        return await self._p_jar.get_child(self._p_oid, key)

    async def __delitem__(self, key):
        return await self._p_jar.delete(await self.__getitem__(key))

    async def get(self, key, default=None):
        try:
            return await self._p_jar.get_child(self._p_oid, key)
        except KeyError:
            return default

    async def __len__(self):
        return await self._p_jar.len(self._p_oid)

    async def keys(self):
        return await self._p_jar.keys(self._p_oid)

    async def items(self):
        async for key, value in self._p_jar.items(self._p_oid):
            yield key, value


@configure.contenttype(portal_type="Site", schema=ISite)
class Site(Folder):

    async def install(self):
        # Creating and registering a local registry
        from guillotina.registry import Registry
        registry = Registry()
        await apply_coroutine(self.__setitem__, '_registry', registry)

        # Set default plugins
        registry.register_interface(ILayers)
        registry.register_interface(IAddons)
        layers = registry.for_interface(ILayers)
        layers.__setattr__(
            'active_layers',
            frozenset('guillotina.interfaces.layer.IDefaultLayer'))

        roles = IPrincipalRoleManager(self)
        roles.assign_role_to_principal(
            'guillotina.SiteAdmin',
            ROOT_USER_ID
        )

        roles.assign_role_to_principal(
            'guillotina.Owner',
            ROOT_USER_ID
        )


@implementer(IStaticFile)
class StaticFile(object):
    def __init__(self, file_path: pathlib.Path):
        self.file_path = file_path


@implementer(IStaticDirectory)
class StaticDirectory(dict):
    """
    Using dict makes this a simple container so traversing works
    """

    def __init__(self, file_path: pathlib.Path):
        self.file_path = file_path
        for x in file_path.iterdir():
            if not x.name.startswith('.') and '/' not in x.name:
                self[x.name] = StaticFile(x)


@configure.adapter(for_=IStaticFile, provides=IPrincipalPermissionManager)
@configure.adapter(for_=IStaticDirectory, provides=IPrincipalPermissionManager)
class StaticFileSpecialPermissions(PrincipalPermissionManager):
    def __init__(self, db):
        super(StaticFileSpecialPermissions, self).__init__()
        self.grant_permission_to_principal('guillotina.AccessContent', ANONYMOUS_USER_ID)

from copy import deepcopy
from datetime import datetime
from dateutil.tz import tzutc
from guillotina import configure
from guillotina._cache import BEHAVIOR_CACHE
from guillotina._cache import FACTORY_CACHE
from guillotina._cache import PERMISSIONS_CACHE
from guillotina._cache import SCHEMA_CACHE
from guillotina._settings import app_settings
from guillotina.auth.users import ANONYMOUS_USER_ID
from guillotina.auth.users import ROOT_USER_ID
from guillotina.behaviors import apply_markers
from guillotina.browser import get_physical_path
from guillotina.component import get_utilities_for
from guillotina.component import get_utility
from guillotina.component import query_utility
from guillotina.component.factory import Factory
from guillotina.db import oid
from guillotina.event import notify
from guillotina.events import BeforeObjectAddedEvent
from guillotina.events import ObjectLoadedEvent
from guillotina.exceptions import ConflictIdOnContainer
from guillotina.exceptions import InvalidContentType
from guillotina.exceptions import NoPermissionToAdd
from guillotina.exceptions import NotAllowedContentType
from guillotina.interfaces import DEFAULT_ADD_PERMISSION
from guillotina.interfaces import IAddons
from guillotina.interfaces import IAnnotations
from guillotina.interfaces import IAsyncBehavior
from guillotina.interfaces import IBehavior
from guillotina.interfaces import IConstrainTypes
from guillotina.interfaces import IContainer
from guillotina.interfaces import IFolder
from guillotina.interfaces import IGetOwner
from guillotina.interfaces import IInteraction
from guillotina.interfaces import IItem
from guillotina.interfaces import IJavaScriptApplication
from guillotina.interfaces import ILayers
from guillotina.interfaces import IPermission
from guillotina.interfaces import IPrincipalPermissionManager
from guillotina.interfaces import IPrincipalRoleManager
from guillotina.interfaces import IResource
from guillotina.interfaces import IResourceFactory
from guillotina.interfaces import IStaticDirectory
from guillotina.interfaces import IStaticFile
from guillotina.profile import profilable
from guillotina.registry import REGISTRY_DATA_KEY
from guillotina.schema.interfaces import IContextAwareDefaultFactory
from guillotina.security.security_code import PrincipalPermissionManager
from guillotina.transactions import get_transaction
from guillotina.utils import get_current_request
from zope.interface import alsoProvides
from zope.interface import implementer
from zope.interface import Interface
from zope.interface import noLongerProvides
from zope.interface.interfaces import ComponentLookupError

import guillotina.db.orm.base
import os
import pathlib
import typing


_zone = tzutc()  # utz tz is much faster than local tz info
_marker = object()


@implementer(IResourceFactory)
class ResourceFactory(Factory):
    type_name = None
    schema = None
    behaviors = None
    add_permission = None

    def __init__(self, klass, title='', description='',
                 type_name='', schema=None, behaviors=None,
                 add_permission=DEFAULT_ADD_PERMISSION,
                 allowed_types=None):
        super(ResourceFactory, self).__init__(
            klass, title, description,
            tuple(filter(bool, [schema] + list(behaviors) or list())))
        self.type_name = type_name
        self.schema = schema or Interface
        self.behaviors = behaviors or ()
        self.add_permission = add_permission
        self.allowed_types = allowed_types

    @profilable
    def __call__(self, id, parent=None, *args, **kw):
        obj = super(ResourceFactory, self).__call__(*args, **kw)
        if parent is not None:
            obj.__parent__ = parent
        obj.type_name = self.type_name
        now = datetime.now(tz=_zone)
        obj.creation_date = now
        obj.modification_date = now
        if id is None:
            if obj._p_oid is None:
                obj._p_oid = app_settings['oid_generator'](obj)
            obj.id = oid.get_short_oid(obj._p_oid)
        else:
            obj.id = id
        obj.__name__ = obj.id
        apply_markers(obj)
        return obj

    @profilable
    def get_interfaces(self):
        spec = super(ResourceFactory, self).get_interfaces()
        spec.__name__ = self.type_name
        return spec

    def __repr__(self):
        return '<{0:s} for {1:s}>'.format(self.__class__.__name__,
                                          self.type_name)


def load_cached_schema():
    for x in get_utilities_for(IResourceFactory):
        factory = x[1]
        if factory.type_name not in SCHEMA_CACHE:
            FACTORY_CACHE[factory.type_name] = factory
            behaviors_registrations = []
            for iface in factory.behaviors or ():
                if Interface.providedBy(iface):
                    name = iface.__identifier__
                else:
                    name = iface
                behaviors_registrations.append(get_utility(IBehavior, name=name))
            SCHEMA_CACHE[factory.type_name] = {
                'behaviors': behaviors_registrations,
                'schema': factory.schema
            }
    for iface, utility in get_utilities_for(IBehavior):
        if isinstance(iface, str):
            name = iface
        elif Interface.providedBy(iface):
            name = iface.__identifier__
        if name not in BEHAVIOR_CACHE:
            BEHAVIOR_CACHE[name] = utility.interface


def get_cached_factory(type_name):
    if type_name in FACTORY_CACHE:
        factory = FACTORY_CACHE[type_name]
    else:
        try:
            factory = get_utility(IResourceFactory, type_name)
        except ComponentLookupError:
            raise InvalidContentType(type_name)
        FACTORY_CACHE[type_name] = factory
    return factory


def iter_schemata_for_type(type_name):
    factory = get_cached_factory(type_name)
    if factory.schema is not None:
        yield factory.schema
    for schema in factory.behaviors or ():
        yield schema


def get_all_possible_schemas_for_type(type_name):
    result = set()
    factory = get_cached_factory(type_name)
    if factory.schema is not None:
        result.add(factory.schema)
    for schema in factory.behaviors or ():
        result.add(schema)
    for _, utility in get_utilities_for(IBehavior):
        if utility.for_.isEqualOrExtendedBy(factory.schema):
            result.add(utility.interface)
    return [b for b in result]


def iter_schemata(obj):
    type_name = obj.type_name
    for schema in iter_schemata_for_type(type_name):
        yield schema
    for schema in obj.__behaviors_schemas__:
        yield schema


@profilable
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
    obj.__new_marker__ = True
    return obj


@profilable
async def create_content_in_container(container, type_, id_, request=None,
                                      check_security=True, **kw):
    """Utility to create a content.

    This method is the one to use to create content.
    id_ can be None
    """
    factory = get_cached_factory(type_)

    if check_security and factory.add_permission:
        if factory.add_permission in PERMISSIONS_CACHE:
            permission = PERMISSIONS_CACHE[factory.add_permission]
        else:
            permission = query_utility(IPermission, name=factory.add_permission)
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
    obj = factory(id=id_, parent=container)
    for key, value in kw.items():
        setattr(obj, key, value)

    txn = getattr(container, '_p_jar', None) or get_transaction()
    if txn is None or not txn.storage.supports_unique_constraints:
        # need to manually check unique constraints
        if await container.async_contains(obj.id):
            raise ConflictIdOnContainer(f'Duplicate ID: {container} -> {obj.id}')

    obj.__new_marker__ = True

    await notify(BeforeObjectAddedEvent(obj, container, id_))
    await container.async_set(obj.id, obj)
    return obj


def get_all_behavior_interfaces(content) -> list:
    factory = get_cached_factory(content.type_name)
    behaviors = []
    for behavior_schema in factory.behaviors or ():
        behaviors.append(behavior_schema)

    for dynamic_behavior in content.__behaviors_schemas__:
        behaviors.append(dynamic_behavior)
    return behaviors


async def get_all_behaviors(content, create=False, load=True) -> list:
    behaviors = []
    for behavior_schema in get_all_behavior_interfaces(content):
        behavior = behavior_schema(content)
        if load:
            if IAsyncBehavior.implementedBy(behavior.__class__):  # pylint: disable=E1120
                # providedBy not working here?
                await behavior.load(create=create)
        behaviors.append((behavior_schema, behavior))
    return behaviors


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


@implementer(IResource)
class Resource(guillotina.db.orm.base.BaseObject):
    """
    Base resource object class
    """

    __behaviors__ = frozenset({})
    __acl__ = None

    type_name = None
    creation_date = None
    modification_date = None
    title = None

    @property
    def uuid(self):
        """
        The unique id of the content object
        """
        return self._p_oid

    def __init__(self, id: str=None):
        if id is not None:
            self.__name__ = id
        super(Resource, self).__init__()

    def __repr__(self):
        """
        """
        path = '/'.join(get_physical_path(self))
        return "< {type} at {path} by {mem} >".format(
            type=self.type_name,
            path=path,
            mem=id(self))

    @property
    def acl(self) -> dict:
        """
        Access control list stores security information on the object
        """
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

    def add_behavior(self, iface: Interface) -> None:
        """We need to apply the marker interface.

        value: Interface to add
        """
        if isinstance(iface, str):
            name = iface
        elif Interface.providedBy(iface):
            name = iface.__identifier__
        else:
            raise AttributeError('Cant identify Interface')
        behavior_registration = get_utility(IBehavior, name=name)
        if behavior_registration is not None and\
                behavior_registration.interface(self) is not None:
            # We can adapt so we can apply this dynamic behavior
            self.__behaviors__ |= {name}
            if behavior_registration.marker is not None:
                alsoProvides(self, behavior_registration.marker)
            self._p_register()  # make sure we resave this obj

    def remove_behavior(self, iface: Interface) -> None:
        """We need to apply the marker interface.

        value: Interface to add
        """
        if isinstance(iface, str):
            name = iface
        elif Interface.providedBy(iface):
            name = iface.__identifier__
        behavior_registration = get_utility(IBehavior, name=name)
        if (behavior_registration is not None and
                behavior_registration.marker is not None):
            try:
                noLongerProvides(self, behavior_registration.marker)
            except ValueError:
                # could not remove interface
                pass
        if iface in self.__behaviors__:
            self.__behaviors__ -= {name}
        self._p_register()  # make sure we resave this obj

    @profilable
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
            SCHEMA_CACHE.get(self.type_name, {}).get('schema'),
            name
        )
        if value is not _marker:
            return value
        raise AttributeError(name)


@configure.contenttype(
    type_name="Item",
    schema=IItem,
    behaviors=["guillotina.behaviors.dublincore.IDublinCore"])
class Item(Resource):
    """
    Basic item content type. Inherits from Resource
    """


@configure.contenttype(
    type_name="Folder",
    schema=IFolder,
    behaviors=["guillotina.behaviors.dublincore.IDublinCore"])
class Folder(Resource):
    """
    Basic folder content type. Inherits from Resource but provides interface
    to work with contained objects asynchronously.
    """

    def _get_transaction(self):
        if self._p_jar is not None:
            return self._p_jar
        return get_transaction()

    async def async_contains(self, key: str) -> bool:
        """
        Asynchronously check if key exists inside this folder
        """
        return await self._get_transaction().contains(self._p_oid, key)

    async def async_set(self, key: str, value: IResource) -> None:
        """
        Asynchronously set an object in this folder
        """
        value.__parent__ = self
        value.__name__ = key
        trns = self._get_transaction()
        if trns is not None:
            value._p_jar = trns
            trns.register(value)

    async def async_get(self, key: str, default=None, suppress_events=False) -> IResource:
        """
        Asynchronously get an object inside this folder
        """
        try:
            val = await self._get_transaction().get_child(self, key)
            if val is not None:
                if not suppress_events:
                    await notify(ObjectLoadedEvent(val))
                return val
        except KeyError:
            pass
        return default

    async def async_multi_get(self, keys: typing.List[str], default=None,
                              suppress_events=False) -> typing.Iterator[typing.Tuple[str, IResource]]:  # noqa
        """
        Asynchronously get an object inside this folder
        """
        async for item in self._get_transaction().get_children(self, keys):
            yield item

    async def async_del(self, key: str) -> None:
        """
        Asynchronously delete object in the folder
        """
        return self._get_transaction().delete(await self.async_get(key))

    async def async_len(self) -> int:
        """
        Asynchronously calculate the len of the folder
        """
        return await self._get_transaction().len(self._p_oid)

    async def async_keys(self) -> typing.List[str]:
        """
        Asynchronously get the sub object keys in this folder
        """
        return await self._get_transaction().keys(self._p_oid)

    async def async_items(self, suppress_events=False) -> typing.Iterator[typing.Tuple[str, IResource]]:  # noqa
        """
        Asynchronously iterate through contents of folder
        """
        async for key, value in self._get_transaction().items(self):
            if not suppress_events:
                await notify(ObjectLoadedEvent(value))
            yield key, value

    async def async_values(self, suppress_events=False) -> typing.Iterator[typing.Tuple[str, IResource]]:  # noqa
        async for _, value in self._get_transaction().items(self):
            if not suppress_events:
                await notify(ObjectLoadedEvent(value))
            yield value


@configure.contenttype(type_name="Container", schema=IContainer)
class Container(Folder):
    """
    """

    async def install(self):
        # Creating and registering a local registry
        from guillotina.registry import Registry
        annotations_container = IAnnotations(self)
        registry = Registry()
        await annotations_container.async_set(REGISTRY_DATA_KEY, registry)

        # Set default plugins
        registry.register_interface(ILayers)
        registry.register_interface(IAddons)
        layers = registry.for_interface(ILayers)
        layers['active_layers'] = frozenset()

        roles = IPrincipalRoleManager(self)
        roles.assign_role_to_principal(
            'guillotina.ContainerAdmin',
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

    def __init__(self, file_path: pathlib.Path, base_path: pathlib.Path=None):
        self.file_path = file_path
        if base_path is None:
            self.base_path = file_path
        else:
            self.base_path = base_path

    def __getitem__(self, filename):
        path = pathlib.Path(os.path.join(self.file_path.absolute(), filename))
        if not path.exists():
            raise KeyError(filename)
        if path.is_dir():
            return StaticDirectory(path, self.base_path)
        else:
            return StaticFile(path)

    def __contains__(self, filename):
        try:
            return self[filename] is not None
        except KeyError:
            return False


@implementer(IJavaScriptApplication)
class JavaScriptApplication(StaticDirectory):
    """
    Same as StaticDirectory; however, it renders /index.html for every
    sub-directory
    """

    def __getitem__(self, filename):
        if filename.lower() in app_settings['default_static_filenames']:
            path = pathlib.Path(os.path.join(self.base_path.absolute(), filename))
            return StaticFile(path)
        path = pathlib.Path(os.path.join(self.file_path.absolute(), filename))
        if path.is_dir() or not path.exists():
            return JavaScriptApplication(path, self.base_path)
        else:
            return StaticFile(path)

    def __contains__(self, filename):
        if not self.file_path.exists():
            # we're in every path is valid mode
            return True
        try:
            return self[filename] is not None
        except KeyError:
            return False


@configure.adapter(for_=IStaticFile, provides=IPrincipalPermissionManager)
@configure.adapter(for_=IStaticDirectory, provides=IPrincipalPermissionManager)
@configure.adapter(for_=IJavaScriptApplication, provides=IPrincipalPermissionManager)
class StaticFileSpecialPermissions(PrincipalPermissionManager):
    def __init__(self, db):
        super(StaticFileSpecialPermissions, self).__init__()
        self.grant_permission_to_principal('guillotina.AccessContent', ANONYMOUS_USER_ID)


@configure.utility(provides=IGetOwner)
async def default_get_owner(obj, creator):
    return creator

# -*- coding: utf-8 -*-
from BTrees.Length import Length
from BTrees.OOBTree import OOBTree
from copy import deepcopy
from datetime import datetime
from dateutil.tz import tzlocal
from persistent import Persistent
from plone.behavior.interfaces import IBehavior
from plone.behavior.interfaces import IBehaviorAssignable
from plone.behavior.markers import applyMarkers
from plone.server import BEHAVIOR_CACHE
from plone.server import FACTORY_CACHE
from plone.server import PERMISSIONS_CACHE
from plone.server import SCHEMA_CACHE
from plone.server.auth.users import ANONYMOUS_USER_ID
from plone.server.auth.users import ROOT_USER_ID
from plone.server.browser import get_physical_path
from plone.server.exceptions import NoPermissionToAdd
from plone.server.exceptions import NotAllowedContentType
from plone.server.interfaces import DEFAULT_ADD_PERMISSION
from plone.server.interfaces import IConstrainTypes
from plone.server.interfaces import IContainer
from plone.server.interfaces import IItem
from plone.server.interfaces import IResource
from plone.server.interfaces import IResourceFactory
from plone.server.interfaces import ISite
from plone.server.interfaces import IStaticDirectory
from plone.server.interfaces import IStaticFile
from plone.server.registry import IAddons
from plone.server.registry import ILayers
from plone.server.registry import Registry
from plone.server.transactions import get_current_request
from plone.server.transactions import synccontext
from plone.server.utils import Lazy
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.component import adapter
from zope.component import getUtilitiesFor
from zope.component import getUtility
from zope.component import queryUtility
from zope.component.factory import Factory
from zope.event import notify
from zope.interface import alsoProvides
from zope.interface import implementer
from zope.interface import Interface
from zope.interface import noLongerProvides
from zope.lifecycleevent import ObjectAddedEvent
from zope.lifecycleevent import ObjectRemovedEvent
from zope.schema.interfaces import IContextAwareDefaultFactory
from zope.security.interfaces import IPermission
from zope.securitypolicy.interfaces import IPrincipalRoleManager
from zope.securitypolicy.principalpermission import PrincipalPermissionManager

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


def create_content(type_, **kw):
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


def create_content_in_container(container, type_, id_, request=None, **kw):
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
                not request.security.checkPermission(permission.id, container):
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
        if obj.id in container:
            raise KeyError('Key already exist on this container')
    container[obj.id] = obj
    return obj


@implementer(IBehaviorAssignable)
@adapter(IResource)
class BehaviorAssignable(object):
    """Support plone.behavior behaviors stored on the CACHE
    """

    def __init__(self, context):
        self.context = context

    def supports(self, behavior_interface):
        """We support all behaviors that accomplish the for_."""
        return True

    def enumerateBehaviors(self):
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
class Resource(Persistent):

    __name__ = None
    __parent__ = None
    __behaviors__ = frozenset({})

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


@implementer(IItem)
class Item(Resource):
    pass


@implementer(IContainer)
class Folder(Resource):

    def __init__(self, id_=None):
        self._Folder__data = OOBTree()
        self.__len = Length()
        super(Folder, self).__init__()

    def __contains__(self, key):
        return key in self.__data

    @Lazy
    def _Folder__len(self):
        l = Length()
        ol = len(self.__data)
        if ol > 0:
            l.change(ol)
        self._p_changed = True
        return l

    def __len__(self):
        return self.__len()

    def __iter__(self):
        return iter(self.__data)

    def __getitem__(self, key):
        return self.__data[key]

    def get(self, key, default=None):
        return self.__data.get(key, default)

    async def asyncget(self, key):
        return await synccontext(self)(self.__data.__getitem__, key)

    def __setitem__(self, key, value):
        l = self.__len
        self.__data[key] = value
        value.__parent__ = self
        l.change(1)
        notify(ObjectAddedEvent(value, self, key))

    def __delitem__(self, key):
        l = self.__len
        item = self.__data[key]
        del self.__data[key]
        l.change(-1)
        notify(ObjectRemovedEvent(item, self, item.__name__))

    has_key = __contains__

    def items(self, key=None):
        return self.__data.items(key)

    def keys(self, key=None):
        return self.__data.keys(key)

    def values(self, key=None):
        return self.__data.values(key)

    def __repr__(self):
        path = '/'.join([name or 'n/a' for name in get_physical_path(self)])
        return "< {type} at {path} by {mem} >".format(
            type=self.portal_type,
            path=path,
            mem=id(self))


@implementer(ISite)
class Site(Folder):

    def install(self):
        # Creating and registering a local registry
        self['_registry'] = registry = Registry()

        # Set default plugins
        registry.register_interface(ILayers)
        registry.register_interface(IAddons)
        registry.for_interface(ILayers).active_layers =\
            frozenset({'plone.server.api.layer.IDefaultLayer'})

        roles = IPrincipalRoleManager(self)
        roles.assignRoleToPrincipal(
            'plone.SiteAdmin',
            ROOT_USER_ID
        )

        roles.assignRoleToPrincipal(
            'plone.Owner',
            ROOT_USER_ID
        )


@implementer(IStaticFile)
class StaticFile(object):
    def __init__(self, file_path):
        self._file_path = file_path


@implementer(IStaticDirectory)
class StaticDirectory(object):

    _items = {}

    def __init__(self, file_path):
        self._file_path = file_path
        for x in file_path.iterdir():
            if not x.name.startswith('.') and '/' not in x.name:
                self._items[x.name] = StaticFile(str(x.absolute()))


class StaticFileSpecialPermissions(PrincipalPermissionManager):
    def __init__(self, db):
        super(StaticFileSpecialPermissions, self).__init__()
        self.grantPermissionToPrincipal('plone.AccessContent', ANONYMOUS_USER_ID)

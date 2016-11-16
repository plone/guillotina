# -*- coding: utf-8 -*-
import uuid
from datetime import datetime
from dateutil.tz import tzlocal
from BTrees.Length import Length
from BTrees.OOBTree import OOBTree
from persistent import Persistent
from plone.behavior.markers import applyMarkers
from plone.behavior.interfaces import IBehaviorAssignable
from plone.server.browser import get_physical_path
from plone.server.interfaces import DEFAULT_ADD_PERMISSION
from plone.server.interfaces import IContainer
from plone.server.interfaces import IItem
from plone.server.interfaces import IRegistry
from plone.server.interfaces import IResource
from plone.server.interfaces import IResourceFactory
from plone.server.interfaces import ISite
from plone.server.interfaces import IStaticDirectory
from plone.server.interfaces import IStaticFile
from plone.server import SCHEMA_CACHE
from plone.server import PERMISSIONS_CACHE
from plone.server import FACTORY_CACHE
from plone.behavior.interfaces import IBehavior
from plone.server.registry import IAddons
from plone.server.registry import ILayers
from plone.server.registry import Registry
from plone.server.utils import Lazy
from plone.server.transactions import synccontext
from plone.server.transactions import get_current_request
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.component import getUtility
from zope.component.factory import Factory
from zope.security.interfaces import IPermission
from zope.component import queryUtility
from zope.component import adapter
from zope.component.persistentregistry import PersistentComponents
from zope.event import notify
from zope.interface import implementer
from zope.interface import Interface
from zope.lifecycleevent import ObjectAddedEvent
from zope.lifecycleevent import ObjectRemovedEvent
from zope.securitypolicy.interfaces import IPrincipalRoleManager
from zope.securitypolicy.principalpermission import PrincipalPermissionManager

_zone = tzlocal()


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

    def __call__(self, *args, **kw):
        if self.portal_type not in SCHEMA_CACHE:
            behaviors_registrations = []
            for iface in self.behaviors or ():
                if Interface.providedBy(iface):
                    name = iface.__identifier__
                else:
                    name = iface
                behaviors_registrations.append(getUtility(IBehavior, name=name))
            SCHEMA_CACHE[self.portal_type] = {
                'behaviors': behaviors_registrations,
                'schema': self.schema
            }

        obj = super(ResourceFactory, self).__call__(*args, **kw)
        obj.portal_type = self.portal_type
        now = datetime.now(tz=_zone)
        obj.creation_date = now
        obj.modification_date = now
        obj.uuid = uuid.uuid4().hex
        applyMarkers(obj, None)
        return obj

    def getInterfaces(self):
        spec = super(ResourceFactory, self).getInterfaces()
        spec.__name__ = self.portal_type
        return spec

    def __repr__(self):
        return '<{0:s} for {1:s}>'.format(self.__class__.__name__,
                                          self.portal_type)


def getCachedFactory(portal_type):
    if portal_type in FACTORY_CACHE:
        factory = FACTORY_CACHE[portal_type]
    else:
        factory = getUtility(IResourceFactory, portal_type)
        FACTORY_CACHE[portal_type] = factory
    return factory


def iterSchemataForType(portal_type):
    factory = getCachedFactory(portal_type)
    if factory.schema is not None:
        yield factory.schema
    for schema in factory.behaviors or ():
        yield schema


def iterSchemata(obj):
    portal_type = IResource(obj).portal_type
    for schema in iterSchemataForType(portal_type):
        yield schema


class NotAllowedContentType(Exception):

    def __init__(self, container, content_type):
        self.container = container
        self.content_type = content_type

    def __repr__(self):
        return "Not allowed {content_type} on {path}".format(
            content_type=self.content_type,
            path=self.path)


class NoPermissionToAdd(Exception):

    def __init__(self, container, content_type):
        self.container = container
        self.content_type = content_type

    def __repr__(self):
        return "Not permission to add {content_type} on {path}".format(
            content_type=self.content_type,
            path=self.path)


def createContent(type_, **kw):
    """Utility to create a content.
    
    This method should not be used to add content, just internally.
    """
    factory = getCachedFactory(type_)
    obj = factory()
    for key, value in kw.items():
        setattr(obj, key, value)
    return obj


def createContentInContainer(container, type_, id_, request=None, **kw):
    """Utility to create a content.

    This method is the one to use to create content.
    """
    factory = getCachedFactory(type_)

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

    if factory.allowed_types is not None and \
            type_ not in factory.allowed_types:
        raise NotAllowedContentType(str(container), type_)
    obj = factory()
    obj.__name__ = id_
    obj.__parent__ = container
    container[id_] = obj
    for key, value in kw.items():
        setattr(obj, key, value)
    return obj


@implementer(IBehaviorAssignable)
@adapter(IResource)
class BehaviorAssignable(object):
    """Support plone.behavior behaviors stored on the CACHE
    """

    def __init__(self, context):
        self.context = context

    def supports(self, behavior_interface):
        for behavior in self.enumerateBehaviors():
            if behavior_interface in behavior.interface._implied:
                return True
        return False

    def enumerateBehaviors(self):
        for behavior in SCHEMA_CACHE[self.context.portal_type]['behaviors']:
            yield behavior


@implementer(IResource, IAttributeAnnotatable)
class Resource(Persistent):

    __name__ = None
    __parent__ = None

    portal_type = None
    uuid = None
    creation_date = None
    modification_date = None

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
        self['_components'] = components = PersistentComponents()

        # Creating and registering a local registry
        self['_registry'] = registry = Registry()
        components.registerUtility(
            self['_registry'], provided=IRegistry)

        # Set default plugins
        registry.registerInterface(ILayers)
        registry.registerInterface(IAddons)
        registry.forInterface(ILayers).active_layers =\
            frozenset({'plone.server.api.layer.IDefaultLayer'})

        roles = IPrincipalRoleManager(self)
        roles.assignRoleToPrincipal(
            'plone.SiteAdmin',
            'RootUser'
        )

        roles.assignRoleToPrincipal(
            'plone.Owner',
            'RootUser'
        )

    def getSiteManager(self):
        return self['_components']

    def setSiteManager(self, sitemanager):
        self['_components'] = sitemanager


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
        self.grantPermissionToPrincipal('plone.AccessContent', 'Anonymous User')

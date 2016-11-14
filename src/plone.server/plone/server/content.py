# -*- coding: utf-8 -*-
from BTrees.OOBTree import OOBTree
from BTrees.Length import Length
from persistent import Persistent
from persistent.mapping import PersistentMapping
from plone.behavior.annotation import AnnotationsFactoryImpl
from plone.server.browser import get_physical_path
from plone.server.interfaces import DEFAULT_ADD_PERMISSION
from plone.server.interfaces import IContainer
from plone.server.interfaces import IItem
from plone.server.interfaces import ISite
from plone.server.interfaces import IRegistry
from plone.server.interfaces import IResource
from plone.server.interfaces import IResourceFactory
from plone.server.interfaces import IStaticDirectory
from plone.server.interfaces import IStaticFile
from plone.server.registry import IAddons
from plone.server.registry import IAuthExtractionPlugins
from plone.server.registry import IAuthPloneUserPlugins
from plone.server.registry import ICors
from plone.server.registry import ILayers
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.component import getUtility
from zope.component.factory import Factory
from zope.component.interfaces import IFactory
from zope.component.persistentregistry import PersistentComponents
from zope.interface import implementer
from zope.interface import Interface
from zope.interface.declarations import alsoProvides
from zope.securitypolicy.interfaces import IPrincipalRoleManager
from zope.securitypolicy.principalpermission import PrincipalPermissionManager
from zope.lifecycleevent import ObjectAddedEvent
from zope.lifecycleevent import ObjectRemovedEvent
from zope.event import notify


class RecordsProxy(AnnotationsFactoryImpl):

    # noinspection PyMissingConstructor
    def __init__(self, context, iface, prefix=None):
        self.__dict__['schema'] = iface
        self.__dict__['prefix'] = iface.__identifier__ + '.'
        self.__dict__['annotations'] = context
        alsoProvides(self, iface)

        if prefix is not None:
            self.__dict__['prefix'] = prefix + '.'


@implementer(IRegistry)
class Registry(PersistentMapping):

    def __init__(self):
        self._data = OOBTree()
        super(Registry, self).__init__()

    def forInterface(self, iface, check=True, omit=(), prefix=None):
        return RecordsProxy(self, iface, prefix=prefix)

    def registerInterface(self, iface, omit=(), prefix=None):
        proxy = self.forInterface(iface)
        for name in iface.names():
            if name in omit:
                continue
            setattr(proxy, name, None)


@implementer(IResourceFactory)
class ResourceFactory(Persistent, Factory):
    portal_type = None
    schema = None
    behaviors = None
    add_permission = None

    def __init__(self, klass, title='', description='',
                 portal_type='', schema=None, behaviors=None,
                 add_permission=DEFAULT_ADD_PERMISSION):
        super(ResourceFactory, self).__init__(
            klass, title, description,
            tuple(filter(bool, [schema] + list(behaviors) or list())))
        self.portal_type = portal_type
        self.schema = schema or Interface
        self.behaviors = behaviors or ()
        self.add_permission = add_permission

    def __call__(self, *args, **kw):
        obj = super(ResourceFactory, self).__call__(*args, **kw)
        obj.portal_type = self.portal_type
        return obj

    def getInterfaces(self):
        spec = super(ResourceFactory, self).getInterfaces()
        spec.__name__ = self.portal_type
        return spec

    def __repr__(self):
        return '<{0:s} for {1:s}>'.format(self.__class__.__name__,
                                          self.portal_type)


def iterSchemataForType(portal_type):
    factory = getUtility(IResourceFactory, portal_type)
    if factory.schema is not None:
        yield factory.schema
    for schema in factory.behaviors or ():
        yield schema


def iterSchemata(obj):
    portal_type = IResource(obj).portal_type
    for schema in iterSchemataForType(portal_type):
        yield schema


# def isConstructionAllowed(factory, container, request=None):
#     if not factory.add_permission:
#        return False

#   permission = queryUtility(IPermission, name=factory.add_permission)
#   if permission is None:
#       return False

#   return request.security.checkPermission(permission.id, container)


def createContent(type_, **kw):
    factory = getUtility(IFactory, type_)
    obj = factory()
    for key, value in kw.items():
        setattr(obj, key, value)
    return obj


def createContentInContainer(container, type_, id_, **kw):
    factory = getUtility(IFactory, type_)
    obj = factory()
    obj.__name__ = id_
    obj.__parent__ = container
    container[id_] = obj
    for key, value in kw.items():
        setattr(obj, key, value)
    return obj


@implementer(IItem, IAttributeAnnotatable)
class Item(Persistent):

    __name__ = None
    __parent__ = None

    portal_type = None

    def __init__(self, id_=None):
        if id_ is not None:
            self.__name__ = id_
        super(Item, self).__init__()

    def __repr__(self):
        path = '/'.join(get_physical_path(self))
        return "< {type} at {path} by {mem} >".format(
            type=self.portal_type,
            path=path,
            mem=id(self))


@implementer(IContainer, IAttributeAnnotatable)
class Folder(PersistentMapping):

    __name__ = None
    __parent__ = None

    portal_type = None

    def __init__(self, id_=None):
        if id_ is not None:
            self.__name__ = id_
        self._data = OOBTree()
        self._length = Length()
        super(Folder, self).__init__()

    def __len__(self):
        return self._length()

    def __setitem__(self, key, value):
        super(Folder, self).__setitem__(key, value)
        l = self._length
        value.__parent__ = self
        l.change(1)
        notify(ObjectAddedEvent(value, self, key))

    def __delitem__(self, key):
        super(Folder, self).__delitem__(key)
        item = self._data[key]
        l = self._length
        l.change(-1)
        notify(ObjectRemovedEvent(item, self, item.__name__))

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
        registry.registerInterface(IAuthPloneUserPlugins)
        registry.registerInterface(IAuthExtractionPlugins)
        registry.registerInterface(ICors)
        registry.registerInterface(IAddons)
        registry.forInterface(ILayers).active_layers =\
            frozenset({'plone.server.api.layer.IDefaultLayer'})

        registry.forInterface(ICors).enabled = True
        registry.forInterface(ICors).allow_origin = frozenset({'*'})
        registry.forInterface(ICors).allow_methods = frozenset({
            'GET', 'POST', 'DELETE',
            'HEAD', 'PATCH'})
        registry.forInterface(ICors).allow_headers = frozenset({'*'})
        registry.forInterface(ICors).expose_headers = frozenset({'*'})
        registry.forInterface(ICors).allow_credentials = True
        registry.forInterface(ICors).max_age = '3660'

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

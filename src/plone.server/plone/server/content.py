# -*- coding: utf-8 -*-
from plone.dexterity.content import Container
from plone.registry import Registry
from plone.registry.interfaces import IRegistry
from plone.server.interfaces import IPloneSite
from plone.server.interfaces import IItem
from plone.server.interfaces import IStaticFile
from plone.server.interfaces import IStaticDirectory
from plone.server.registry import IAuthExtractionPlugins
from plone.server.registry import IAuthPloneUserPlugins
from plone.server.registry import ILayers
from plone.server.registry import ICors
from plone.server.registry import IAddons

from zope.component.persistentregistry import PersistentComponents
from zope.interface import implementer
from zope.securitypolicy.principalpermission import PrincipalPermissionManager
from plone.server.browser import get_physical_path


@implementer(IPloneSite)
class PloneSite(Container):

    def __init__(self, *args, **kwargs):
        super(PloneSite, self).__init__(*args, **kwargs)

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
        registry.forInterface(ILayers).active_layers = \
            ['plone.server.api.layer.IDefaultLayer']
        registry.forInterface(IAuthExtractionPlugins).active_plugins = \
            ['plone.server.auth.oauth.PloneJWTExtraction']
        registry.forInterface(IAuthPloneUserPlugins).active_plugins = \
            ['plone.server.auth.oauth.OAuthPloneUserFactory']

        registry.forInterface(ICors).enabled = True
        registry.forInterface(ICors).allow_origin = ['*']
        registry.forInterface(ICors).allow_methods = ['GET', 'POST', 'DELETE',
                                                      'HEAD', 'PATCH']
        registry.forInterface(ICors).allow_headers = ['*']
        registry.forInterface(ICors).expose_headers = ['*']
        registry.forInterface(ICors).allow_credentials = True
        registry.forInterface(ICors).max_age = '3660'

    def getSiteManager(self):
        return self['_components']

    def setSiteManager(self, sitemanager):
        self['_components'] = sitemanager


@implementer(IItem)
class Item(Container):

    def __repr__(self):
        path = '/'.join(get_physical_path(self))
        return "< {type} at {path} by {mem} >".format(
            type=self.portal_type,
            path=path,
            mem=id(self))


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

# -*- coding: utf-8 -*-
from plone.dexterity.content import Container
from plone.registry import Registry
from plone.registry.interfaces import IRegistry
from plone.server.interfaces import IPloneSite
from plone.server.registry import IAuthExtractionPlugins
from plone.server.registry import IAuthPloneUserPlugins
from plone.server.registry import ILayers
from zope.component.persistentregistry import PersistentComponents
from zope.interface import implementer
from zope.securitypolicy.interfaces import IPrincipalPermissionManager
from zope.securitypolicy.interfaces import IRolePermissionManager


@implementer(IPloneSite)
class PloneSite(Container):

    def __init__(self, *args, **kwargs):
        super(PloneSite, self).__init__(*args, **kwargs)
        self['_components'] = components = PersistentComponents()

        # Creating and registering a local registry
        self['_registry'] = registry = Registry()
        components.registerUtility(
            self['_registry'], provided=IRegistry)

        # Set default plugins
        registry.registerInterface(ILayers)
        registry.registerInterface(IAuthPloneUserPlugins)
        registry.registerInterface(IAuthExtractionPlugins)
        registry.forInterface(ILayers).active_layers = \
            ['plone.server.api.layer.IDefaultLayer']
        registry.forInterface(IAuthExtractionPlugins).active_plugins = \
            ['plone.server.auth.oauth.PloneJWTExtraction']
        registry.forInterface(IAuthPloneUserPlugins).active_plugins = \
            ['plone.server.auth.oauth.OAuthPloneUserFactory']

        # Default policy
        roles = IRolePermissionManager(self)
        roles.grantPermissionToRole(
            'plone.AccessContent',
            'Anonymous User'
        )
        roles.grantPermissionToRole(
            'plone.ViewContent',
            'Anonymous User'
        )

        roles = IPrincipalPermissionManager(self)
        roles.grantPermissionToPrincipal(
            'plone.AccessContent',
            'Anonymous User'
        )
        roles.grantPermissionToPrincipal(
            'plone.AccessContent',
            'plone.manager'
        )

        roles = IRolePermissionManager(self)
        roles.grantPermissionToRole(
            'plone.AccessContent',
            'Manager'
        )
        roles.grantPermissionToRole(
            'plone.AccessContent',
            'plone.manager'
        )

    def getSiteManager(self):
        return self['_components']

    def setSiteManager(self, sitemanager):
        self['_components'] = sitemanager


class StaticFile(object):
    def __init__(self, file_path):
        self._file_path = file_path

    
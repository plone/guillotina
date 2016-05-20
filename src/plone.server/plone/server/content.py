# -*- coding: utf-8 -*-
from zope.securitypolicy.interfaces import IRolePermissionManager
from plone.dexterity.content import Container
from plone.registry import Registry
from plone.registry.interfaces import IRegistry
from plone.server.auth.oauth import IPloneJWTExtractionConfig
from plone.server.auth.oauth import IPloneOAuthConfig
from plone.server.interfaces import IPloneSite
from zope.component.persistentregistry import PersistentComponents
from zope.interface import implementer
from plone.server.registry import ILayers
from plone.server.registry import IAuthPloneUserPlugins
from plone.server.registry import IAuthExtractionPlugins
from plone.server.interfaces import DEFAULT_READ_PERMISSION


@implementer(IPloneSite)
class PloneSite(Container):

    def __init__(self, *args, **kwargs):
        super(Site, self).__init__(*args, **kwargs)
        self['_components'] = components = PersistentComponents()

        # Creating and registering a local registry
        self['_registry'] = registry = Registry()
        components.registerUtility(self['_registry'],
                                            provided=IRegistry)

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
        registry.registerInterface(IPloneJWTExtractionConfig)
        registry.registerInterface(IPloneOAuthConfig)

        # Default policy
        roles = IRolePermissionManager(self)
        roles.grantPermissionForRole(
            DEFAULT_READ_PERMISSION,
            'Anonymous User'
        )

    def getSiteManager(self):
        return self['_components']

    def setSiteManager(self, sitemanager):
        self['_components'] = sitemanager


Site = PloneSite  # BBB

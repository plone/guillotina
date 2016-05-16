# -*- coding: utf-8 -*-
from plone.dexterity.content import Container
from plone.server.interfaces import IPloneSite
from zope.component.persistentregistry import PersistentComponents
from zope.interface import implementer


# noinspection PyPep8Naming
@implementer(IPloneSite)
class Site(Container):

    def __init__(self):
        super(Site, self).__init__()
        self['_components'] = PersistentComponents()

    def getSiteManager(self):
        return self['_components']

    def setSiteManager(self, sitemanager):
        self['_components'] = sitemanager

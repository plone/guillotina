from plone.server.content import Container

from zope.component.interfaces import ISite
from zope.component.persistentregistry import PersistentComponents

from zope.interface import implementer


@implementer(ISite)
class Site(Container):

    def __init__(self):
        self['_components'] = PersistentComponents()

    def getSiteManager(self):
        return self['_components']

    def setSiteManager(self, sitemanager):
        self['_components'] = sitemanager

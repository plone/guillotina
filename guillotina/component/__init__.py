##############################################################################
#
# Copyright (c) 2001, 2002 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
# flake8: noqa
from zope.interface import Interface
from zope.interface import implementedBy
from zope.interface import moduleProvides
from zope.interface import named
from zope.interface import providedBy

from guillotina.component.interfaces import ComponentLookupError
from guillotina.component.interfaces import IComponentArchitecture
from guillotina.component.interfaces import IComponentLookup
from guillotina.component.interfaces import IComponentRegistrationConvenience
from guillotina.component.interfaces import IFactory

from guillotina.component.globalregistry import getGlobalSiteManager
from guillotina.component.globalregistry import globalSiteManager
from guillotina.component.globalregistry import provideAdapter
from guillotina.component.globalregistry import provideHandler
from guillotina.component.globalregistry import provideSubscriptionAdapter
from guillotina.component.globalregistry import provideUtility

from guillotina.component._api import adapter_hook
from guillotina.component._api import getAdapter
from guillotina.component._api import getAdapterInContext
from guillotina.component._api import getAdapters
from guillotina.component._api import getAllUtilitiesRegisteredFor
from guillotina.component._api import getFactoriesFor
from guillotina.component._api import getFactoryInterfaces
from guillotina.component._api import getMultiAdapter
from guillotina.component._api import getSiteManager
from guillotina.component._api import getUtilitiesFor
from guillotina.component._api import getUtility
from guillotina.component._api import handle
from guillotina.component._api import queryAdapter
from guillotina.component._api import queryAdapterInContext
from guillotina.component._api import queryMultiAdapter
from guillotina.component._api import queryUtility
from guillotina.component._api import subscribers

from guillotina.component._declaration import adaptedBy
from guillotina.component._declaration import adapter
from guillotina.component._declaration import adapts

moduleProvides(IComponentArchitecture, IComponentRegistrationConvenience)
__all__ = tuple(IComponentArchitecture)

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
from guillotina.component._api import get_adapter
from guillotina.component._api import get_adapters
from guillotina.component._api import get_all_utilities_registered_for
from guillotina.component._api import get_component_registry
from guillotina.component._api import get_factories_for
from guillotina.component._api import get_factory_interfaces
from guillotina.component._api import get_multi_adapter
from guillotina.component._api import get_utilities_for
from guillotina.component._api import get_utility
from guillotina.component._api import handle
from guillotina.component._api import query_adapter
from guillotina.component._api import query_multi_adapter
from guillotina.component._api import query_utility
from guillotina.component._api import subscribers
from guillotina.component._declaration import adaptedBy
from guillotina.component._declaration import adapter
from guillotina.component._declaration import adapts
from guillotina.component.globalregistry import get_global_components
from guillotina.component.globalregistry import provide_adapter
from guillotina.component.globalregistry import provide_handler
from guillotina.component.globalregistry import provide_subscription_adapter
from guillotina.component.globalregistry import provide_utility
from guillotina.component.interfaces import ComponentLookupError
from guillotina.component.interfaces import IComponentArchitecture
from guillotina.component.interfaces import IComponentLookup
from guillotina.component.interfaces import IComponentRegistrationConvenience
from guillotina.component.interfaces import IFactory
from zope.interface import moduleProvides


# b/w compat imports. Will be removed in 3.0
getMultiAdapter = get_multi_adapter
queryMultiAdapter = query_multi_adapter
getAdapter = get_adapter
queryAdapter = query_adapter
getUtility = get_utility
queryUtility = query_utility
getUtilitiesFor = get_utilities_for
getAdapters = get_adapters


moduleProvides(IComponentArchitecture, IComponentRegistrationConvenience)
__all__ = tuple(IComponentArchitecture)  # type: ignore

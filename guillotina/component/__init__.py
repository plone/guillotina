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
from zope.interface import moduleProvides

from guillotina.component._api import (
    get_adapter,
    get_adapters,
    get_all_utilities_registered_for,
    get_component_registry,
    get_factories_for,
    get_factory_interfaces,
    get_multi_adapter,
    get_utilities_for,
    get_utility,
    handle,
    query_adapter,
    query_multi_adapter,
    query_utility,
    subscribers,
)
from guillotina.component._declaration import adaptedBy, adapter, adapts
from guillotina.component.globalregistry import (
    get_global_components,
    provide_adapter,
    provide_handler,
    provide_subscription_adapter,
    provide_utility,
)
from guillotina.component.interfaces import (
    ComponentLookupError,
    IComponentArchitecture,
    IComponentLookup,
    IComponentRegistrationConvenience,
    IFactory,
)


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

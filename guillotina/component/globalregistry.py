##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
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
from guillotina.component._compat import _BLANK
from guillotina.component.interfaces import IComponentLookup
from zope.interface import implementer
from zope.interface.adapter import AdapterRegistry
from zope.interface.registry import Components


def GAR(components, registryName):
    return getattr(components, registryName)

class GlobalAdapterRegistry(AdapterRegistry):
    """A global adapter registry

    This adapter registry's main purpose is to be picklable in combination
    with a site manager."""

    def __init__(self, parent, name):
        self.__parent__ = parent
        self.__name__ = name
        super(GlobalAdapterRegistry, self).__init__()

    def __reduce__(self):
        return GAR, (self.__parent__, self.__name__)


@implementer(IComponentLookup)
class GlobalComponents(Components):

    def _init_registries(self):
        self.adapters = GlobalAdapterRegistry(self, 'adapters')
        self.utilities = GlobalAdapterRegistry(self, 'utilities')

    def __reduce__(self):
        # Global site managers are pickled as global objects
        return self.__name__


base = GlobalComponents('base')


def get_global_components():
    return base


def provide_utility(component, provides=None, name=_BLANK):
    base.registerUtility(component, provides, name, event=False)

def provide_adapter(factory, adapts=None, provides=None, name=_BLANK):
    base.registerAdapter(factory, adapts, provides, name, event=False)

def provide_subscription_adapter(factory, adapts=None, provides=None):
    base.registerSubscriptionAdapter(factory, adapts, provides, event=False)

def provide_handler(factory, adapts=None):
    base.registerHandler(factory, adapts, event=False)

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
from guillotina.component import globalregistry
from guillotina.component._compat import _BLANK
from guillotina.component._declaration import adapter  # noqa
from guillotina.component.hookable import hookable
from guillotina.component.interfaces import ComponentLookupError
from guillotina.component.interfaces import IComponentLookup
from guillotina.component.interfaces import IFactory
from zope.interface import Interface
from zope.interface import providedBy

import zope.interface.interface

_MISSING = object()


@hookable
def get_component_registry(context=None):
    """ See IComponentArchitecture.
    """
    if context is None:
        return globalregistry.base
    else:
        # Use the global site manager to adapt context to `IComponentLookup`
        # to avoid the recursion implied by using a local `get_adapter()` call.
        try:
            return IComponentLookup(context)
        except TypeError as error:
            raise ComponentLookupError(*error.args)


def get_adapter(object, interface=Interface, name=_BLANK, context=None,
                args=[], kwargs={}):
    '''
    Get a registered adapter

    :param object: Object to get adapter for
    :param interface: What interface should the adapter provide
    :param name: if it is a named adapter
    :param args: args to provide the adapter constructor
    :param kwargs: kwargs to provide the adapter constructor
    :raises ComponentLookupError:
    '''
    adapter_ = query_adapter(object, interface=interface, name=name,
                             default=_MISSING, context=context,
                             args=args, kwargs=kwargs)
    if adapter_ is _MISSING:
        # result from get_adapter can be None and still be valid
        raise ComponentLookupError(object, interface, name)
    return adapter_


def query_adapter(object, interface=Interface, name=_BLANK, default=None,
                  context=None, args=[], kwargs={}):
    '''
    Get a registered adapter

    :param object: Object to get adapter for
    :param interface: What interface should the adapter provide
    :param name: if it is a named adapter
    :param args: args to provide the adapter constructor
    :param kwargs: kwargs to provide the adapter constructor
    '''
    if context is None:
        return adapter_hook(interface, object,
                            name=name, default=default,
                            args=args, kwargs=kwargs)
    return get_component_registry(context).queryAdapter(
        object, interface, name, default)


def get_multi_adapter(objects, interface=Interface, name=_BLANK, context=None,
                      args=[], kwargs={}):
    '''
    Get a registered multi adapter

    :param objects: Objects to get adapter for
    :param interface: What interface should the adapter provide
    :param name: if it is a named adapter
    :param args: args to provide the adapter constructor
    :param kwargs: kwargs to provide the adapter constructor
    :raises ComponentLookupError:
    '''
    adapter_ = query_multi_adapter(
        objects, interface, name, context=context, args=args, kwargs=kwargs)
    if adapter_ is None:
        raise ComponentLookupError(objects, interface, name)
    return adapter_


def query_multi_adapter(objects, interface=Interface, name=_BLANK, default=None,
                        context=None, args=[], kwargs={}):
    '''
    Get a registered multi adapter

    :param objects: Objects to get adapter for
    :param interface: What interface should the adapter provide
    :param name: if it is a named adapter
    :param args: args to provide the adapter constructor
    :param kwargs: kwargs to provide the adapter constructor
    '''
    try:
        registry = get_component_registry(context)
    except ComponentLookupError:
        # Oh blast, no site manager. This should *never* happen!
        return default

    factory = registry.adapters.lookup(map(providedBy, objects), interface, name)
    if factory is None:
        return default

    result = factory(*objects, *args, **kwargs)
    if result is None:
        return default

    return result


def get_adapters(objects, provided, context=None):
    '''
    Get a registered adapter

    :param objects: Tuple of objects
    :param provided: What interface should the adapter provide
    '''
    try:
        registry = get_component_registry(context)
    except ComponentLookupError:
        # Oh blast, no site manager. This should *never* happen!
        return []
    return registry.getAdapters(objects, provided)


def subscribers(objects, interface, context=None):
    try:
        registry = get_component_registry(context)
    except ComponentLookupError:
        # Oh blast, no site manager. This should *never* happen!
        return []
    return registry.subscribers(objects, interface)


def handle(*objects):
    get_component_registry(None).subscribers(objects, None)

#############################################################################
# Register the component architectures adapter hook, with the adapter hook
# registry of the `zope.inteface` package. This way we will be able to call
# interfaces to create adapters for objects.


@hookable
def adapter_hook(interface, object, name='', default=None, args=[], kwargs={}):
    try:
        registry = get_component_registry()
    except ComponentLookupError:  # pragma NO COVER w/o context, cannot test
        # Oh blast, no site manager. This should *never* happen!
        return None

    factory = registry.adapters.lookup((providedBy(object),), interface, name)
    if factory is None:
        return default

    return factory(object, *args, **kwargs)


zope.interface.interface.adapter_hooks.append(adapter_hook)
#############################################################################


# Utility API

def get_utility(interface, name='', context=None):
    '''
    Get a registered utility

    :param interface: What interface should the utility provide
    :param name: if it is a named adapter
    :raises ComponentLookupError:
    '''
    utility = query_utility(interface, name, context=context)
    if utility is not None:
        return utility
    raise ComponentLookupError(interface, name)


def query_utility(interface, name='', default=None, context=None):
    '''
    Get a registered utility

    :param interface: What interface should the utility provide
    :param name: if it is a named adapter
    '''
    return get_component_registry(context).queryUtility(interface, name, default)


def get_utilities_for(interface, context=None):
    '''
    Get utilities registered for interface

    :param interface: What interface should the utility provide
    '''
    return get_component_registry(context).getUtilitiesFor(interface)


def get_all_utilities_registered_for(interface, context=None):
    '''
    Get all utilities registered for interface

    :param interface: What interface should the utility provide
    '''
    return get_component_registry(context).getAllUtilitiesRegisteredFor(interface)


_marker = object()


def get_factory_interfaces(name, context=None):
    """Return the interface provided by the named factory's objects

    Result might be a single interface. XXX
    """
    return get_utility(IFactory, name, context).get_interfaces()


def get_factories_for(interface, context=None):
    """Return info on all factories implementing the given interface.
    """
    utils = get_component_registry(context)
    for (name, factory) in utils.getUtilitiesFor(IFactory):
        interfaces = factory.get_interfaces()
        try:
            if interfaces.isOrExtends(interface):
                yield name, factory
        except AttributeError:
            for iface in interfaces:
                if iface.isOrExtends(interface):
                    yield name, factory
                    break

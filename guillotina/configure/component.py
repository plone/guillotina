##############################################################################
#
# Copyright (c) 2005 Zope Foundation and Contributors.
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
"""Component Architecture configuration handlers
"""
from guillotina.component._api import getSiteManager
from guillotina.component._compat import _BLANK
from guillotina.component._declaration import adaptedBy
from guillotina.component._declaration import getName
from guillotina.component.interface import provideInterface
from guillotina.exceptions import ComponentConfigurationError
from guillotina.i18n import MessageFactory
from zope.interface import implementedBy
from zope.interface import Interface
from zope.interface import providedBy


_ = MessageFactory('guillotina')


def handler(methodName, *args, **kwargs):
    method = getattr(getSiteManager(), methodName)
    method(*args, **kwargs)


def _rolledUpFactory(factories):
    # This has to be named 'factory', aparently, so as not to confuse
    # apidoc :(
    def factory(ob):
        for f in factories:
            ob = f(ob)
        return ob
    # Store the original factory for documentation
    factory.factory = factories[0]
    return factory


def adapter(_context, factory, provides=None, for_=None, name=''):

    if for_ is None:
        if len(factory) == 1:
            for_ = adaptedBy(factory[0])

        if for_ is None:
            raise TypeError("No for attribute was provided and can't "
                            "determine what the factory adapts.")

    for_ = tuple(for_)

    if provides is None:
        if len(factory) == 1:
            p = list(implementedBy(factory[0]))
            if len(p) == 1:
                provides = p[0]

        if provides is None:
            raise TypeError("Missing 'provides' attribute")

    if name == '':
        if len(factory) == 1:
            name = getName(factory[0])

    # Generate a single factory from multiple factories:
    factories = factory
    if len(factories) == 1:
        factory = factories[0]
    elif len(factories) < 1:
        raise ComponentConfigurationError("No factory specified")
    elif len(factories) > 1 and len(for_) != 1:
        raise ComponentConfigurationError(
            "Can't use multiple factories and multiple for")
    else:
        factory = _rolledUpFactory(factories)

    _context.action(
        discriminator=('adapter', for_, provides, name),
        callable=handler,
        args=('registerAdapter', factory, for_, provides, name))
    _context.action(
        discriminator=None,
        callable=provideInterface,
        args=('', provides))
    if for_:
        for iface in for_:
            if iface is not None:
                _context.action(
                    discriminator=None,
                    callable=provideInterface,
                    args=('', iface))


_handler = handler


def subscriber(_context, for_=None, factory=None, handler=None, provides=None):
    if factory is None:
        if handler is None:
            raise TypeError("No factory or handler provided")
        if provides is not None:
            raise TypeError("Cannot use handler with provides")
        factory = handler
    else:
        if handler is not None:
            raise TypeError("Cannot use handler with factory")
        if provides is None:
            raise TypeError(
                "You must specify a provided interface when registering "
                "a factory")

    if for_ is None:
        for_ = adaptedBy(factory)
        if for_ is None:
            raise TypeError("No for attribute was provided and can't "
                            "determine what the factory (or handler) adapts.")

    for_ = tuple(for_)

    if handler is not None:
        _context.action(
            discriminator=None,
            callable=_handler,
            args=('registerHandler', handler, for_, _BLANK))
    else:
        _context.action(
            discriminator=None,
            callable=_handler,
            args=('registerSubscriptionAdapter', factory, for_, provides, _BLANK))

    if provides is not None:
        _context.action(
            discriminator=None,
            callable=provideInterface,
            args=('', provides))

    # For each interface, state that the adapter provides that interface.
    for iface in for_:
        if iface is not None:
            _context.action(
                discriminator=None,
                callable=provideInterface,
                args=('', iface))


def utility(_context, provides=None, component=None, factory=None, name=''):
    if factory and component:
        raise TypeError("Can't specify factory and component.")

    if provides is None:
        if factory:
            provides = list(implementedBy(factory))
        else:
            provides = list(providedBy(component))
        if len(provides) == 1:
            provides = provides[0]
        else:
            raise TypeError("Missing 'provides' attribute")

    if name == '':
        if factory:
            name = getName(factory)
        else:
            name = getName(component)

    _context.action(
        discriminator=('utility', provides, name),
        callable=handler,
        args=('registerUtility', component, provides, name),
        kw=dict(factory=factory))
    _context.action(
        discriminator=None,
        callable=provideInterface,
        args=('', provides))


def interface(_context, interface, type=None, name=''):
    _context.action(
        discriminator=None,
        callable=provideInterface,
        args=(name, interface, type))


def view(_context, factory, type, name, for_, provides=Interface):

    if not for_:
        raise ComponentConfigurationError("No for interfaces specified")
    for_ = tuple(for_)

    # Generate a single factory from multiple factories:
    factories = factory
    if len(factories) == 1:
        factory = factories[0]
    elif len(factories) < 1:
        raise ComponentConfigurationError("No view factory specified")
    elif len(factories) > 1 and len(for_) > 1:
        raise ComponentConfigurationError(
            "Can't use multiple factories and multiple for")
    else:
        def factory(ob, request):
            for f in factories[:-1]:
                ob = f(ob)
            return factories[-1](ob, request)
        factory.factory = factories[0]

    for_ = for_ + (type,)

    _context.action(
        discriminator=('view', for_, name, provides),
        callable=handler,
        args=('registerAdapter', factory, for_, provides, name))

    _context.action(
        discriminator=None,
        callable=provideInterface,
        args=('', provides))

    if for_ is not None:
        for iface in for_:
            if iface is not None:
                _context.action(
                    discriminator=None,
                    callable=provideInterface,
                    args=('', iface))


def resource(_context, factory, type, name, provides=Interface):

    _context.action(
        discriminator=('resource', name, type, provides),
        callable=handler,
        args=('registerAdapter', factory, (type,), provides, name))
    _context.action(
        discriminator=None,
        callable=provideInterface,
        args=('', type))
    _context.action(
        discriminator=None,
        callable=provideInterface,
        args=('', provides))

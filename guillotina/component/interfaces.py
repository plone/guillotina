############################################################################
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
############################################################################
# flake8: noqa

# fmt: off
from guillotina.component._compat import _BLANK
from zope.interface import Attribute
from zope.interface import Interface
# BBB 2011-09-09, import interfaces from zope.interface
from zope.interface.interfaces import _IBaseAdapterRegistration
from zope.interface.interfaces import ComponentLookupError
from zope.interface.interfaces import IAdapterRegistration
from zope.interface.interfaces import IComponentLookup
from zope.interface.interfaces import IComponentRegistry
from zope.interface.interfaces import IComponents
from zope.interface.interfaces import IHandlerRegistration
from zope.interface.interfaces import Invalid
from zope.interface.interfaces import IObjectEvent
from zope.interface.interfaces import IRegistered
from zope.interface.interfaces import IRegistration
from zope.interface.interfaces import IRegistrationEvent
from zope.interface.interfaces import ISubscriptionAdapterRegistration
from zope.interface.interfaces import IUnregistered
from zope.interface.interfaces import IUtilityRegistration
from zope.interface.interfaces import ObjectEvent
from zope.interface.interfaces import Registered
from zope.interface.interfaces import RegistrationEvent
from zope.interface.interfaces import Unregistered


# fmt: on


class IComponentArchitecture(Interface):
    """The Component Architecture is defined by two key components: Adapters
    and Utiltities. Both are managed by site managers. All other components
    build on top of them.
    """

    # Site Manager API

    def get_global_components():  # type: ignore
        """Return the global site manager.

        This function should never fail and always return an object that
        provides `IGlobalSiteManager`.
        """

    def get_component_registry(context=None):
        """Get the nearest site manager in the given context.

        If `context` is `None`, return the global site manager.

        If the `context` is not `None`, it is expected that an adapter
        from the `context` to `IComponentLookup` can be found. If no
        adapter is found, a `ComponentLookupError` is raised.

        """

    # Utility API

    def get_utility(interface, name="", context=None):
        """Get the utility that provides interface

        Returns the nearest utility to the context that implements the
        specified interface.  If one is not found, raises
        ComponentLookupError.
        """

    def query_utility(interface, name="", default=None, context=None):
        """Look for the utility that provides interface

        Returns the nearest utility to the context that implements
        the specified interface.  If one is not found, returns default.
        """

    def get_utilities_for(interface, context=None):
        """Return the utilities that provide an interface

        An iterable of utility name-value pairs is returned.
        """

    def get_all_utilities_registered_for(interface, context=None):
        """Return all registered utilities for an interface

        This includes overridden utilities.

        An iterable of utility instances is returned.  No names are
        returned.
        """

    # Adapter API

    def get_adapter(object, interface=Interface, name=_BLANK, context=None):
        """Get a named adapter to an interface for an object

        Returns an adapter that can adapt object to interface.  If a matching
        adapter cannot be found, raises ComponentLookupError.

        If context is None, an application-defined policy is used to choose
        an appropriate service manager from which to get an 'Adapters' service.

        If 'context' is not None, context is adapted to IServiceService,
        and this adapter's 'Adapters' service is used.
        """

    def get_multi_adapter(objects, interface=Interface, name="", context=None):
        """Look for a multi-adapter to an interface for an objects

        Returns a multi-adapter that can adapt objects to interface.  If a
        matching adapter cannot be found, raises ComponentLookupError.

        If context is None, an application-defined policy is used to choose
        an appropriate service manager from which to get an 'Adapters' service.

        If 'context' is not None, context is adapted to IServiceService,
        and this adapter's 'Adapters' service is used.

        The name consisting of an empty string is reserved for unnamed
        adapters. The unnamed adapter methods will often call the
        named adapter methods with an empty string for a name.
        """

    def query_adapter(object, interface=Interface, name=_BLANK, default=None, context=None):
        """Look for a named adapter to an interface for an object

        Returns an adapter that can adapt object to interface.  If a matching
        adapter cannot be found, returns the default.

        If context is None, an application-defined policy is used to choose
        an appropriate service manager from which to get an 'Adapters' service.

        If 'context' is not None, context is adapted to IServiceService,
        and this adapter's 'Adapters' service is used.
        """

    def query_multi_adapter(objects, interface=Interface, name=_BLANK, default=None, context=None):
        """Look for a multi-adapter to an interface for objects

        Returns a multi-adapter that can adapt objects to interface.  If a
        matching adapter cannot be found, returns the default.

        If context is None, an application-defined policy is used to choose
        an appropriate service manager from which to get an 'Adapters' service.

        If 'context' is not None, context is adapted to IServiceService,
        and this adapter's 'Adapters' service is used.

        The name consisting of an empty string is reserved for unnamed
        adapters. The unnamed adapter methods will often call the
        named adapter methods with an empty string for a name.
        """

    def get_adapters(objects, provided, context=None):
        """Look for all matching adapters to a provided interface for objects

        Return a list of adapters that match. If an adapter is named, only the
        most specific adapter of a given name is returned.

        If context is None, an application-defined policy is used to choose
        an appropriate service manager from which to get an 'Adapters'
        service.

        If 'context' is not None, context is adapted to IServiceService,
        and this adapter's 'Adapters' service is used.
        """

    def subscribers(required, provided, context=None):
        """Get subscribers

        Subscribers are returned that provide the provided interface
        and that depend on and are computed from the sequence of
        required objects.

        If context is None, an application-defined policy is used to choose
        an appropriate service manager from which to get an 'Adapters'
        service.

        If 'context' is not None, context is adapted to IServiceService,
        and this adapter's 'Adapters' service is used.
        """

    def handle(*objects):
        """Call all of the handlers for the given objects

        Handlers are subscription adapter factories that don't produce
        anything.  They do all of their work when called.  Handlers
        are typically used to handle events.

        """

    def adapts(*interfaces):
        """Declare that a class adapts the given interfaces.

        This function can only be used in a class definition.

        (TODO, allow classes to be passed as well as interfaces.)
        """

    # Factory service
    def get_factory_interfaces(name, context=None):
        """Get interfaces implemented by a factory

        Finds the factory of the given name that is nearest to the
        context, and returns the interface or interface tuple that
        object instances created by the named factory will implement.
        """

    def get_factories_for(interface, context=None):
        """Return a tuple (name, factory) of registered factories that
        create objects which implement the given interface.
        """


class IRegistry(Interface):
    """Object that supports component registry"""

    def registrations():  # type: ignore
        """Return an iterable of component registrations"""


class IComponentRegistrationConvenience(Interface):
    """API for registering components.

    CAUTION: This API should only be used from test or
    application-setup code. This api shouldn't be used by regular
    library modules, as component registration is a configuration
    activity.
    """

    def provide_utility(component, provides=None, name=_BLANK):
        """Register a utility globally

        A utility is registered to provide an interface with a
        name. If a component provides only one interface, then the
        provides argument can be omitted and the provided interface
        will be used. (In this case, provides argument can still be
        provided to provide a less specific interface.)

        CAUTION: This API should only be used from test or
        application-setup code. This API shouldn't be used by regular
        library modules, as component registration is a configuration
        activity.

        """

    def provide_adapter(factory, adapts=None, provides=None, name=_BLANK):
        """Register an adapter globally

        An adapter is registered to provide an interface with a name
        for some number of object types. If a factory implements only
        one interface, then the provides argument can be omitted and
        the provided interface will be used. (In this case, a provides
        argument can still be provided to provide a less specific
        interface.)

        If the factory has an adapts declaration, then the adapts
        argument can be omitted and the declaration will be used.  (An
        adapts argument can be provided to override the declaration.)

        CAUTION: This API should only be used from test or
        application-setup code. This API shouldn't be used by regular
        library modules, as component registration is a configuration
        activity.
        """

    def provide_subscription_adapter(factory, adapts=None, provides=None):
        """Register a subscription adapter

        A subscription adapter is registered to provide an interface
        for some number of object types. If a factory implements only
        one interface, then the provides argument can be omitted and
        the provided interface will be used. (In this case, a provides
        argument can still be provided to provide a less specific
        interface.)

        If the factory has an adapts declaration, then the adapts
        argument can be omitted and the declaration will be used.  (An
        adapts argument can be provided to override the declaration.)

        CAUTION: This API should only be used from test or
        application-setup code. This API shouldn't be used by regular
        library modules, as component registration is a configuration
        activity.
        """

    def provide_handler(handler, adapts=None):
        """Register a handler

        Handlers are subscription adapter factories that don't produce
        anything.  They do all of their work when called.  Handlers
        are typically used to handle events.

        If the handler has an adapts declaration, then the adapts
        argument can be omitted and the declaration will be used.  (An
        adapts argument can be provided to override the declaration.)

        CAUTION: This API should only be used from test or
        application-setup code. This API shouldn't be used by regular
        library modules, as component registration is a configuration
        activity.
        """


class ISite(Interface):
    """Marker interface to indicate that we have a site"""

    def setSiteManager(sitemanager):
        """Sets the site manager for this object."""

    def get_component_registry():  # type: ignore
        """Returns the site manager contained in this object.

        If there isn't a site manager, raise a component lookup.
        """


class IFactory(Interface):
    """A factory is responsible for creating other components."""

    title = Attribute("The factory title.")

    description = Attribute("A brief description of the factory.")

    def __call__(*args, **kw):
        """Return an instance of the objects we're a factory for."""

    def get_interfaces():  # type: ignore
        """Get the interfaces implemented by the factory

        Return the interface(s), as an instance of Implements, that objects
        created by this factory will implement. If the callable's Implements
        instance cannot be created, an empty Implements instance is returned.
        """

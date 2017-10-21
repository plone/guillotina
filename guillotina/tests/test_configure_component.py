##############################################################################
#
# Copyright (c) 2012 Zope Foundation and Contributors.
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
"""Tests for ZCML directives.
"""
import unittest


class Test_handler(unittest.TestCase):  # noqa: N801

    def _callFUT(self, *args, **kw):  # noqa: N802
        from guillotina.configure.component import handler
        return handler(*args, **kw)

    def test_uses_configured_site_manager(self):
        from zope.interface.registry import Components
        from guillotina.component import get_component_registry
        from guillotina.component.testfiles.components import comp, IApp
        from guillotina.component._compat import _BLANK

        registry = Components()

        def dummy(context=None):
            return registry
        get_component_registry.sethook(dummy)

        try:
            self._callFUT('registerUtility', comp, IApp, _BLANK)
            self.assertTrue(registry.getUtility(IApp) is comp)
        finally:
            get_component_registry.reset()


class Test__rolledUpFactory(unittest.TestCase):  # noqa: N801

    def _callFUT(self, *args, **kw):  # noqa: N802
        from guillotina.configure.component import _rolledUpFactory
        return _rolledUpFactory(*args, **kw)

    def test_with_one(self):
        _OBJ = object()
        _CREATED = object()

        def _factory(obj):
            return _CREATED
        rolled = self._callFUT([_factory])
        self.assertTrue(rolled.factory is _factory)
        self.assertTrue(rolled(_OBJ) is _CREATED)

    def test_with_multiple(self):
        _OBJ = object()
        _CREATED1 = object()
        _CREATED2 = object()
        _CREATED3 = object()

        def _factory1(obj):
            return _CREATED1

        def _factory2(obj):
            return _CREATED2

        def _factory3(obj):
            return _CREATED3
        rolled = self._callFUT([_factory1, _factory2, _factory3])
        self.assertTrue(rolled.factory is _factory1)
        self.assertTrue(rolled(_OBJ) is _CREATED3)


class Test_adapter(unittest.TestCase):  # noqa: N801

    def _callFUT(self, *args, **kw):  # noqa: N802
        from guillotina.configure.component import adapter
        return adapter(*args, **kw)

    def test_empty_factory(self):
        from zope.interface import Interface
        from guillotina.configure.component import ComponentConfigurationError

        class IFoo(Interface):
            pass
        _cfg_ctx = _makeConfigContext()
        self.assertRaises(ComponentConfigurationError,
                          self._callFUT, _cfg_ctx, [], [Interface], IFoo)

    def test_multiple_factory_multiple_for_(self):
        from zope.interface import Interface
        from guillotina.configure.component import ComponentConfigurationError

        class IFoo(Interface):
            pass

        class IBar(Interface):
            pass

        class Foo(object):
            pass

        class Bar(object):
            pass

        _cfg_ctx = _makeConfigContext()
        self.assertRaises(ComponentConfigurationError,
                          self._callFUT, _cfg_ctx, [Foo, Bar],
                          [Interface, IBar], IFoo)

    def test_no_for__factory_not_adapt(self):
        # @adapter(IFoo)
        class _Factory(object):
            def __init__(self, context):
                self.context = context
        _cfg_ctx = _makeConfigContext()
        self.assertRaises(TypeError, self._callFUT, _cfg_ctx, [_Factory])

    def test_no_name(self):
        from zope.interface import Interface

        class IFoo(Interface):
            pass

        class IBar(Interface):
            pass

        from guillotina.component import adapter
        from zope.interface import implementer, named

        @adapter(IFoo)
        @implementer(IBar)
        @named('bar')
        class _Factory(object):
            def __init__(self, context):
                self.context = context
        _cfg_ctx = _makeConfigContext()
        self._callFUT(_cfg_ctx, [_Factory])
        # Register the adapter
        action = _cfg_ctx._actions[0][1]
        self.assertEqual(action['args'][4], 'bar')

    def test_no_for__factory_adapts_no_provides_factory_not_implement(self):
        from zope.interface import Interface
        from guillotina.component._declaration import adapter

        @adapter(Interface)
        class _Factory(object):
            def __init__(self, context):
                self.context = context

        _cfg_ctx = _makeConfigContext()
        self.assertRaises(TypeError, self._callFUT, _cfg_ctx, [_Factory])

    def test_multiple_factory_single_for__w_name(self):
        from zope.interface import Interface
        from guillotina.component.interface import provide_interface
        from guillotina.configure.component import handler

        class IFoo(Interface):
            pass

        class Foo(object):
            pass

        class Bar(object):
            pass

        _cfg_ctx = _makeConfigContext()
        self._callFUT(_cfg_ctx, [Foo, Bar], IFoo, [Interface], name='test')
        self.assertEqual(len(_cfg_ctx._actions), 3)
        self.assertEqual(_cfg_ctx._actions[0][0], ())
        # Register the adapter
        action = _cfg_ctx._actions[0][1]
        self.assertEqual(action['callable'], handler)
        self.assertEqual(action['discriminator'],
                         ('adapter', (Interface,), IFoo, 'test'))
        self.assertEqual(action['args'][0], 'registerAdapter')
        self.assertEqual(action['args'][1].factory, Foo)  # rolled up
        self.assertEqual(action['args'][2], (Interface,))
        self.assertEqual(action['args'][3], IFoo)
        self.assertEqual(action['args'][4], 'test')
        # Register the provided interface
        self.assertEqual(_cfg_ctx._actions[1][0], ())
        action = _cfg_ctx._actions[1][1]
        self.assertEqual(action['callable'], provide_interface)
        self.assertEqual(action['discriminator'], None)
        self.assertEqual(action['args'], ('', IFoo))
        # Register the required interface(s)
        self.assertEqual(_cfg_ctx._actions[2][0], ())
        action = _cfg_ctx._actions[2][1]
        self.assertEqual(action['callable'], provide_interface)
        self.assertEqual(action['discriminator'], None)
        self.assertEqual(action['args'], ('', Interface))

    def test_no_for__no_provides_factory_adapts_factory_implement(self):
        from zope.interface import Interface
        from zope.interface import implementer
        from guillotina.component._declaration import adapter
        from guillotina.configure.component import handler

        class IFoo(Interface):
            pass

        @adapter(Interface)
        @implementer(IFoo)
        class _Factory(object):
            def __init__(self, context):
                self.context = context
        _cfg_ctx = _makeConfigContext()
        self._callFUT(_cfg_ctx, [_Factory])
        self.assertEqual(len(_cfg_ctx._actions), 3)
        self.assertEqual(_cfg_ctx._actions[0][0], ())
        # Register the adapter
        action = _cfg_ctx._actions[0][1]
        self.assertEqual(action['callable'], handler)
        self.assertEqual(action['discriminator'],
                         ('adapter', (Interface,), IFoo, ''))
        self.assertEqual(action['args'],
                         ('registerAdapter', _Factory, (Interface,), IFoo,
                          ''))


class Test_subscriber(unittest.TestCase):  # noqa: N801

    def _callFUT(self, *args, **kw):  # noqa: N802
        from guillotina.configure.component import subscriber
        return subscriber(*args, **kw)

    def test_no_factory_no_handler(self):
        from zope.interface import Interface
        _cfg_ctx = _makeConfigContext()
        self.assertRaises(TypeError,
                          self._callFUT, _cfg_ctx, (Interface,))

    def test_no_factory_w_handler_w_provides(self):
        from zope.interface import Interface

        class IFoo(Interface):
            pass

        def _handler(*args):
            pass

        _cfg_ctx = _makeConfigContext()
        self.assertRaises(TypeError,
                          self._callFUT, _cfg_ctx, (Interface,),
                          handler=_handler, provides=IFoo)

    def test_w_factory_w_handler(self):
        from zope.interface import Interface

        class Foo(object):
            pass

        def _handler(*args):
            pass
        _cfg_ctx = _makeConfigContext()
        self.assertRaises(TypeError,
                          self._callFUT, _cfg_ctx, (Interface,), Foo,
                          handler=_handler)

    def test_w_factory_no_provides(self):
        from zope.interface import Interface

        class Foo(object):
            pass
        _cfg_ctx = _makeConfigContext()
        self.assertRaises(TypeError,
                          self._callFUT, _cfg_ctx, (Interface,), Foo)

    def test_w_factory_w_provides_no_for_factory_wo_adapter(self):
        from zope.interface import Interface

        class IFoo(Interface):
            pass

        class Foo(object):
            pass
        _cfg_ctx = _makeConfigContext()
        self.assertRaises(TypeError,
                          self._callFUT, _cfg_ctx,
                          factory=Foo, provides=IFoo)

    def test_no_factory_w_handler_no_provides(self):
        from zope.interface import Interface
        from guillotina.component.interface import provide_interface
        from guillotina.configure.component import handler

        def _handler(*args):
            pass
        _cfg_ctx = _makeConfigContext()
        self._callFUT(_cfg_ctx, (Interface,), handler=_handler)
        self.assertEqual(len(_cfg_ctx._actions), 2)
        self.assertEqual(_cfg_ctx._actions[0][0], ())
        # Register the adapter
        action = _cfg_ctx._actions[0][1]
        self.assertEqual(action['callable'], handler)
        self.assertEqual(action['discriminator'], None)
        self.assertEqual(action['args'][0], 'registerHandler')
        self.assertEqual(action['args'][1], _handler)
        self.assertEqual(action['args'][2], (Interface,))
        self.assertEqual(action['args'][3], '')
        # Register the required interface(s)
        self.assertEqual(_cfg_ctx._actions[1][0], ())
        action = _cfg_ctx._actions[1][1]
        self.assertEqual(action['callable'], provide_interface)
        self.assertEqual(action['discriminator'], None)
        self.assertEqual(action['args'], ('', Interface))

    def test_w_factory_w_provides(self):
        from zope.interface import Interface
        from guillotina.component.interface import provide_interface
        from guillotina.configure.component import handler

        class IFoo(Interface):
            pass

        class Foo(object):
            pass

        def _handler(*args):
            pass
        _cfg_ctx = _makeConfigContext()
        self._callFUT(_cfg_ctx, (Interface,), Foo, provides=IFoo)
        self.assertEqual(len(_cfg_ctx._actions), 3)
        self.assertEqual(_cfg_ctx._actions[0][0], ())
        # Register the adapter
        action = _cfg_ctx._actions[0][1]
        self.assertEqual(action['callable'], handler)
        self.assertEqual(action['discriminator'], None)
        self.assertEqual(action['args'][0], 'registerSubscriptionAdapter')
        self.assertEqual(action['args'][1], Foo)
        self.assertEqual(action['args'][2], (Interface,))
        self.assertEqual(action['args'][3], IFoo)
        self.assertEqual(action['args'][4], '')
        # Register the provided interface
        self.assertEqual(_cfg_ctx._actions[1][0], ())
        action = _cfg_ctx._actions[1][1]
        self.assertEqual(action['callable'], provide_interface)
        self.assertEqual(action['discriminator'], None)
        self.assertEqual(action['args'], ('', IFoo))
        # Register the required interface(s)
        self.assertEqual(_cfg_ctx._actions[2][0], ())
        action = _cfg_ctx._actions[2][1]
        self.assertEqual(action['callable'], provide_interface)
        self.assertEqual(action['discriminator'], None)
        self.assertEqual(action['args'], ('', Interface))


class Test_utility(unittest.TestCase):  # noqa: N801

    def _callFUT(self, *args, **kw):  # noqa: N802
        from guillotina.configure.component import utility
        return utility(*args, **kw)

    def test_w_factory_w_component(self):
        class _Factory(object):
            pass
        _COMPONENT = object
        _cfg_ctx = _makeConfigContext()
        self.assertRaises(TypeError, self._callFUT, _cfg_ctx,
                          factory=_Factory, component=_COMPONENT)

    def test_w_factory_wo_provides_factory_no_implement(self):
        class _Factory(object):
            pass
        _cfg_ctx = _makeConfigContext()
        self.assertRaises(TypeError,
                          self._callFUT, _cfg_ctx, factory=_Factory)

    def test_w_component_wo_provides_component_no_provides(self):
        _COMPONENT = object
        _cfg_ctx = _makeConfigContext()
        self.assertRaises(TypeError,
                          self._callFUT, _cfg_ctx, component=_COMPONENT)

    def test_w_factory_w_provides(self):
        from zope.interface import Interface
        from guillotina.component.interface import provide_interface
        from guillotina.configure.component import handler

        class IFoo(Interface):
            pass

        class Foo(object):
            pass
        _cfg_ctx = _makeConfigContext()
        self._callFUT(_cfg_ctx, factory=Foo, provides=IFoo)
        self.assertEqual(len(_cfg_ctx._actions), 2)
        self.assertEqual(_cfg_ctx._actions[0][0], ())
        # Register the utility
        action = _cfg_ctx._actions[0][1]
        self.assertEqual(action['callable'], handler)
        self.assertEqual(action['discriminator'], ('utility', IFoo, ''))
        self.assertEqual(action['args'][0], 'registerUtility')
        self.assertEqual(action['args'][1], None)
        self.assertEqual(action['args'][2], IFoo)
        self.assertEqual(action['args'][3], '')
        self.assertEqual(action['kw'], {'factory': Foo})
        # Register the provided interface
        self.assertEqual(_cfg_ctx._actions[1][0], ())
        action = _cfg_ctx._actions[1][1]
        self.assertEqual(action['callable'], provide_interface)
        self.assertEqual(action['discriminator'], None)
        self.assertEqual(action['args'], ('', IFoo))

    def test_w_factory_wo_provides_factory_implement(self):
        from zope.interface import Interface
        from zope.interface import implementer
        from guillotina.component.interface import provide_interface
        from guillotina.configure.component import handler

        class IFoo(Interface):
            pass

        @implementer(IFoo)
        class Foo(object):
            pass
        _cfg_ctx = _makeConfigContext()
        self._callFUT(_cfg_ctx, factory=Foo)
        self.assertEqual(len(_cfg_ctx._actions), 2)
        self.assertEqual(_cfg_ctx._actions[0][0], ())
        # Register the utility
        action = _cfg_ctx._actions[0][1]
        self.assertEqual(action['callable'], handler)
        self.assertEqual(action['discriminator'], ('utility', IFoo, ''))
        self.assertEqual(action['args'][0], 'registerUtility')
        self.assertEqual(action['args'][1], None)
        self.assertEqual(action['args'][2], IFoo)
        self.assertEqual(action['args'][3], '')
        self.assertEqual(action['kw'], {'factory': Foo})
        # Register the provided interface
        self.assertEqual(_cfg_ctx._actions[1][0], ())
        action = _cfg_ctx._actions[1][1]
        self.assertEqual(action['callable'], provide_interface)
        self.assertEqual(action['discriminator'], None)
        self.assertEqual(action['args'], ('', IFoo))

    def test_w_component_w_provides_w_name(self):
        from zope.interface import Interface
        from guillotina.component.interface import provide_interface
        from guillotina.configure.component import handler

        class IFoo(Interface):
            pass

        _COMPONENT = object()
        _cfg_ctx = _makeConfigContext()
        self._callFUT(_cfg_ctx, component=_COMPONENT,
                      name='test', provides=IFoo)
        self.assertEqual(len(_cfg_ctx._actions), 2)
        self.assertEqual(_cfg_ctx._actions[0][0], ())
        # Register the utility
        action = _cfg_ctx._actions[0][1]
        self.assertEqual(action['callable'], handler)
        self.assertEqual(action['discriminator'], ('utility', IFoo, 'test'))
        self.assertEqual(action['args'][0], 'registerUtility')
        self.assertEqual(action['args'][1], _COMPONENT)
        self.assertEqual(action['args'][2], IFoo)
        self.assertEqual(action['args'][3], 'test')
        # Register the provided interface
        self.assertEqual(_cfg_ctx._actions[1][0], ())
        action = _cfg_ctx._actions[1][1]
        self.assertEqual(action['callable'], provide_interface)
        self.assertEqual(action['discriminator'], None)
        self.assertEqual(action['args'], ('', IFoo))

    def test_w_component_wo_provides_wo_name(self):
        from zope.interface import Interface, implementer, named

        class IFoo(Interface):
            pass

        @implementer(IFoo)
        @named('foo')
        class Foo(object):
            pass
        foo = Foo()
        _cfg_ctx = _makeConfigContext()
        self._callFUT(_cfg_ctx, component=foo)
        action = _cfg_ctx._actions[0][1]
        self.assertEqual(action['args'][1], foo)
        self.assertEqual(action['args'][2], IFoo)
        self.assertEqual(action['args'][3], 'foo')

    def test_w_component_wo_provides_component_provides(self):
        from zope.interface import Interface
        from zope.interface import directlyProvides
        from guillotina.component.interface import provide_interface
        from guillotina.configure.component import handler

        class IFoo(Interface):
            pass

        class Foo(object):
            pass
        _COMPONENT = Foo()
        directlyProvides(_COMPONENT, IFoo)  # noqa
        _cfg_ctx = _makeConfigContext()
        self._callFUT(_cfg_ctx, component=_COMPONENT)
        self.assertEqual(len(_cfg_ctx._actions), 2)
        self.assertEqual(_cfg_ctx._actions[0][0], ())
        # Register the utility
        action = _cfg_ctx._actions[0][1]
        self.assertEqual(action['callable'], handler)
        self.assertEqual(action['discriminator'], ('utility', IFoo, ''))
        self.assertEqual(action['args'][0], 'registerUtility')
        self.assertEqual(action['args'][1], _COMPONENT)
        self.assertEqual(action['args'][2], IFoo)
        self.assertEqual(action['args'][3], '')
        # Register the provided interface
        self.assertEqual(_cfg_ctx._actions[1][0], ())
        action = _cfg_ctx._actions[1][1]
        self.assertEqual(action['callable'], provide_interface)
        self.assertEqual(action['discriminator'], None)
        self.assertEqual(action['args'], ('', IFoo))


class Test_interface(unittest.TestCase):  # noqa: N801

    def _callFUT(self, *args, **kw):  # noqa: N802
        from guillotina.configure.component import interface
        return interface(*args, **kw)

    def test_wo_name_wo_type(self):
        from zope.interface import Interface
        from guillotina.component.interface import provide_interface

        class IFoo(Interface):
            pass

        _cfg_ctx = _makeConfigContext()
        self._callFUT(_cfg_ctx, IFoo)
        self.assertEqual(len(_cfg_ctx._actions), 1)
        self.assertEqual(_cfg_ctx._actions[0][0], ())
        action = _cfg_ctx._actions[0][1]
        self.assertEqual(action['callable'], provide_interface)
        self.assertEqual(action['discriminator'], None)
        self.assertEqual(action['args'], ('', IFoo, None))

    def test_w_name_w_type(self):
        from zope.interface import Interface
        from guillotina.component.interface import provide_interface

        class IFoo(Interface):
            pass

        class IBar(Interface):
            pass

        _cfg_ctx = _makeConfigContext()
        self._callFUT(_cfg_ctx, IFoo, name='foo', type=IBar)
        self.assertEqual(len(_cfg_ctx._actions), 1)
        self.assertEqual(_cfg_ctx._actions[0][0], ())
        action = _cfg_ctx._actions[0][1]
        self.assertEqual(action['callable'], provide_interface)
        self.assertEqual(action['discriminator'], None)
        self.assertEqual(action['args'], ('foo', IFoo, IBar))


class Test_view(unittest.TestCase):  # noqa: N801

    def _callFUT(self, *args, **kw):  # noqa: N802
        from guillotina.configure.component import view
        return view(*args, **kw)

    def test_w_factory_as_empty(self):
        from zope.interface import Interface
        from guillotina.configure.component import ComponentConfigurationError

        class IViewType(Interface):
            pass
        _cfg_ctx = _makeConfigContext()
        self.assertRaises(ComponentConfigurationError,
                          self._callFUT, _cfg_ctx, (), IViewType, '',
                          for_=(Interface, Interface))

    def test_w_multiple_factory_multiple_for_(self):
        from zope.interface import Interface
        from guillotina.configure.component import ComponentConfigurationError

        class IViewType(Interface):
            pass

        class Foo(object):
            pass

        class Bar(object):
            pass
        _cfg_ctx = _makeConfigContext()
        self.assertRaises(ComponentConfigurationError,
                          self._callFUT, _cfg_ctx, (Foo, Bar), IViewType, '',
                          for_=(Interface, Interface))

    def test_w_for__as_empty(self):
        from zope.interface import Interface
        from guillotina.configure.component import ComponentConfigurationError

        class IViewType(Interface):
            pass

        class _View(object):
            def __init__(self, context):
                self.context = context
        _cfg_ctx = _makeConfigContext()
        self.assertRaises(ComponentConfigurationError,
                          self._callFUT, _cfg_ctx, (_View,), IViewType, '',
                          for_=())

    def test_w_single_factory_single_for__wo_permission_w_name(self):
        from zope.interface import Interface
        from guillotina.configure.component import handler
        from guillotina.component.interface import provide_interface

        class IViewType(Interface):
            pass

        class _View(object):
            def __init__(self, context):
                self.context = context
        _cfg_ctx = _makeConfigContext()
        self._callFUT(_cfg_ctx, (_View,), IViewType, 'test', for_=(Interface,))
        self.assertEqual(len(_cfg_ctx._actions), 4)
        self.assertEqual(_cfg_ctx._actions[0][0], ())
        # Register the adapter
        action = _cfg_ctx._actions[0][1]
        self.assertEqual(action['callable'], handler)
        self.assertEqual(action['discriminator'],
                         ('view', (Interface, IViewType), 'test', Interface))
        self.assertEqual(action['args'][0], 'registerAdapter')
        self.assertEqual(action['args'][1], _View)
        self.assertEqual(action['args'][2], (Interface, IViewType))
        self.assertEqual(action['args'][3], Interface)
        self.assertEqual(action['args'][4], 'test')
        # Register the provided interface
        self.assertEqual(_cfg_ctx._actions[1][0], ())
        action = _cfg_ctx._actions[1][1]
        self.assertEqual(action['callable'], provide_interface)
        self.assertEqual(action['discriminator'], None)
        self.assertEqual(action['args'], ('', Interface))
        # Register the required interface(s)
        self.assertEqual(_cfg_ctx._actions[2][0], ())
        action = _cfg_ctx._actions[2][1]
        self.assertEqual(action['callable'], provide_interface)
        self.assertEqual(action['discriminator'], None)
        self.assertEqual(action['args'], ('', Interface))
        self.assertEqual(_cfg_ctx._actions[3][0], ())
        action = _cfg_ctx._actions[3][1]
        self.assertEqual(action['callable'], provide_interface)
        self.assertEqual(action['discriminator'], None)
        self.assertEqual(action['args'], ('', IViewType))

    def test_w_multiple_factory_single_for__wo_permission(self):
        from zope.interface import Interface
        from guillotina.configure.component import handler

        class IViewType(Interface):
            pass

        class _View(object):
            def __init__(self, context):
                self.context = context

        class _View2(object):
            def __init__(self, context, request):
                self.context = context
                self.request = request
        _cfg_ctx = _makeConfigContext()
        self._callFUT(_cfg_ctx, [_View, _View2], IViewType, '',
                      for_=(Interface,))
        self.assertEqual(_cfg_ctx._actions[0][0], ())
        # Register the adapter
        action = _cfg_ctx._actions[0][1]
        self.assertEqual(action['callable'], handler)
        self.assertEqual(action['discriminator'],
                         ('view', (Interface, IViewType), '', Interface))
        self.assertEqual(action['args'][0], 'registerAdapter')
        factory = action['args'][1]
        self.assertTrue(factory.factory is _View)
        context = object()
        request = object()
        view = factory(context, request)
        self.assertTrue(isinstance(view, _View2))
        self.assertTrue(view.request is request)
        self.assertTrue(isinstance(view.context, _View))
        self.assertTrue(view.context.context is context)
        self.assertEqual(action['args'][2], (Interface, IViewType))
        self.assertEqual(action['args'][3], Interface)
        self.assertEqual(action['args'][4], '')


def _makeConfigContext():  # noqa: N802
    class _Context(object):

        def __init__(self):
            self._actions = []

        def action(self, *args, **kw):
            self._actions.append((args, kw))
    return _Context()


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(Test_handler),
        unittest.makeSuite(Test__rolledUpFactory),
        unittest.makeSuite(Test_adapter),
        unittest.makeSuite(Test_subscriber),
        unittest.makeSuite(Test_utility),
        unittest.makeSuite(Test_interface),
        unittest.makeSuite(Test_view)
    ))


def test_configuration_machine_allows_overriding():
    from guillotina.configure.config import ConfigurationMachine
    from guillotina.configure import component
    from guillotina.component import adapter, get_adapter
    from zope.interface import implementer, Interface, named

    class IFoo(Interface):
        pass

    @implementer(IFoo)
    class Foo(object):
        pass

    class IBar(Interface):
        pass

    cm = ConfigurationMachine()

    @adapter(IFoo)
    @implementer(IBar)
    @named('bar')
    class _Factory(object):
        def __init__(self, context):
            self.context = context

    class _FactoryOverride(_Factory):
        pass

    component.adapter(cm, (_Factory,))
    cm.execute_actions()
    cm.commit()

    component.adapter(cm, (_FactoryOverride,))
    cm.execute_actions()

    adapter = get_adapter(Foo(), name='bar')
    assert isinstance(adapter, _FactoryOverride)

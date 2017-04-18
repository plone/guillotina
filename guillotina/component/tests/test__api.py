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
# flake8: noqa
import unittest


class Test_getSiteManager(unittest.TestCase):

    from guillotina.component.testing import setUp, tearDown

    def _callFUT(self, *args, **kw):
        from guillotina.component._api import getSiteManager
        return getSiteManager(*args, **kw)

    def test_sm_is_IComponentLookup(self):
        from guillotina.component.interfaces import IComponentLookup
        sm = self._callFUT()
        self.assertTrue(IComponentLookup.providedBy(sm))

    def test_sm_is_singleton(self):
        from guillotina.component.globalregistry import base
        sm = self._callFUT()
        self.assertTrue(sm is base)
        self.assertTrue(self._callFUT() is sm)

    def test_w_None(self):
        self.assertTrue(self._callFUT(None) is self._callFUT())

    def test_getSiteManager_w_conforming_context(self):
        from guillotina.component.tests.examples import ConformsToIComponentLookup
        sitemanager = object()
        context = ConformsToIComponentLookup(sitemanager)
        self.assertTrue(self._callFUT(context) is sitemanager)

    def test_getSiteManager_w_invalid_context_no_adapter(self):
        from guillotina.component.interfaces import ComponentLookupError
        self.assertRaises(ComponentLookupError, self._callFUT, object())

    def test_getSiteManager_w_invalid_context_w_adapter(self):
        from zope.interface import Interface
        from guillotina.component.globalregistry import getGlobalSiteManager
        from guillotina.component.interfaces import IComponentLookup
        gsm = getGlobalSiteManager()
        sm = object()
        def _adapt(x):
            return sm
        gsm.registerAdapter(_adapt, (Interface,), IComponentLookup, '')
        self.assertTrue(self._callFUT(object()) is sm)


class Test_getAdapterInContext(unittest.TestCase):

    from guillotina.component.testing import setUp, tearDown

    def _callFUT(self, *args, **kw):
        from guillotina.component import getAdapterInContext
        return getAdapterInContext(*args, **kw)

    def test_miss(self):
        from zope.interface import Interface
        from guillotina.component.interfaces import ComponentLookupError
        class IFoo(Interface):
            pass
        self.assertRaises(ComponentLookupError,
                          self._callFUT, object(), IFoo, context=None)

    def test_hit_via_sm(self):
        from zope.interface import Interface
        from zope.interface import implementer
        from zope.interface.registry import Components
        from guillotina.component import getGlobalSiteManager
        from guillotina.component.tests.examples import ConformsToIComponentLookup
        class IFoo(Interface):
            pass
        class IBar(Interface):
            pass
        @implementer(IFoo)
        class Global(object):
            def __init__(self, context):
                self.context = context
        @implementer(IFoo)
        class Local(object):
            def __init__(self, context):
                self.context = context
        @implementer(IBar)
        class Bar(object):
            pass
        class Context(ConformsToIComponentLookup):
            def __init__(self, sm):
                self.sitemanager = sm
        gsm = getGlobalSiteManager()
        gsm.registerAdapter(Global, (IBar,), IFoo, '')
        sm1 = Components('sm1', bases=(gsm, ))
        sm1.registerAdapter(Local, (IBar,), IFoo, '')
        bar = Bar()
        adapted = self._callFUT(bar, IFoo, context=Context(sm1))
        self.assertTrue(adapted.__class__ is Local)
        self.assertTrue(adapted.context is bar)


class Test_queryAdapterInContext(unittest.TestCase):

    from guillotina.component.testing import setUp, tearDown

    def _callFUT(self, *args, **kw):
        from guillotina.component import queryAdapterInContext
        return queryAdapterInContext(*args, **kw)

    def test_miss(self):
        from zope.interface import Interface
        from guillotina.component import queryAdapterInContext
        class IFoo(Interface):
            pass
        self.assertEqual(
            queryAdapterInContext(object(), IFoo, context=None), None)

    def test_w_object_conforming(self):
        from zope.interface import Interface
        from guillotina.component import queryAdapterInContext
        class IFoo(Interface):
            pass
        _adapted = object()
        class Foo(object):
            def __conform__(self, iface, default=None):
                if iface is IFoo:
                    return _adapted
                return default
        self.assertTrue(
                queryAdapterInContext(Foo(), IFoo, context=None) is _adapted)

    def test___conform___raises_TypeError_via_class(self):
        from zope.interface import Interface
        from guillotina.component import queryAdapterInContext
        class IFoo(Interface):
            pass
        _adapted = object()
        class Foo(object):
            def __conform__(self, iface, default=None):
                if iface is IFoo:
                    return _adapted
                return default
        # call via class, triggering TypeError
        self.assertEqual(queryAdapterInContext(Foo, IFoo, context=None), None)

    def test___conform___raises_TypeError_via_inst(self):
        from zope.interface import Interface
        from guillotina.component import queryAdapterInContext
        class IFoo(Interface):
            pass
        _adapted = object()
        class Foo(object):
            def __conform__(self, iface, default=None):
                raise TypeError
        self.assertRaises(TypeError,
                         queryAdapterInContext, Foo(), IFoo, context=None)

    def test_w_object_implementing(self):
        from zope.interface import Interface
        from zope.interface import implementer
        from guillotina.component import queryAdapterInContext
        class IFoo(Interface):
            pass
        @implementer(IFoo)
        class Foo(object):
              pass
        foo = Foo()
        self.assertTrue(
                queryAdapterInContext(foo, IFoo, context=None) is foo)


class Test_getAdapter(unittest.TestCase):

    from guillotina.component.testing import setUp, tearDown

    def _callFUT(self, *args, **kw):
        from guillotina.component import getAdapter
        return getAdapter(*args, **kw)

    def test_anonymous_nonesuch(self):
        from zope.interface import Interface
        from guillotina.component.interfaces import ComponentLookupError
        class IFoo(Interface):
            pass
        self.assertRaises(ComponentLookupError,
                          self._callFUT, object(), IFoo, '')

    def test_named_nonesuch(self):
        from zope.interface import Interface
        from guillotina.component.interfaces import ComponentLookupError
        class IFoo(Interface):
            pass
        self.assertRaises(ComponentLookupError,
                          self._callFUT, object(), IFoo, 'bar')

    def test_anonymous_hit(self):
        from zope.interface import Interface
        from zope.interface import implementer
        from guillotina.component import getGlobalSiteManager
        class IFoo(Interface):
            pass
        class IBar(Interface):
            pass
        @implementer(IBar)
        class Bar(object):
            pass
        @implementer(IFoo)
        class Baz(object):
            def __init__(self, context):
                self.context = context
        getGlobalSiteManager().registerAdapter(Baz, (IBar,), IFoo, '')
        bar = Bar()
        adapted = self._callFUT(bar, IFoo, '')
        self.assertTrue(adapted.__class__ is Baz)
        self.assertTrue(adapted.context is bar)

    def test_anonymous_hit_registered_for_None(self):
        from zope.interface import Interface
        from zope.interface import implementer
        from guillotina.component import getGlobalSiteManager
        class IFoo(Interface):
            pass
        @implementer(IFoo)
        class Baz(object):
            def __init__(self, context):
                self.context = context
        getGlobalSiteManager().registerAdapter(Baz, (None,), IFoo, '')
        ctx = object()
        adapted = self._callFUT(ctx, IFoo, '')
        self.assertTrue(adapted.__class__ is Baz)
        self.assertTrue(adapted.context is ctx)

    def test_named_hit(self):
        from zope.interface import Interface
        from zope.interface import implementer
        from guillotina.component import getGlobalSiteManager
        class IFoo(Interface):
            pass
        class IBar(Interface):
            pass
        @implementer(IBar)
        class Bar(object):
            pass
        @implementer(IFoo)
        class Baz(object):
            def __init__(self, context):
                self.context = context
        getGlobalSiteManager().registerAdapter(Baz, (IBar,), IFoo, 'named')
        bar = Bar()
        adapted = self._callFUT(bar, IFoo, 'named')
        self.assertTrue(adapted.__class__ is Baz)
        self.assertTrue(adapted.context is bar)


class Test_queryAdapter(unittest.TestCase):

    from guillotina.component.testing import setUp, tearDown

    def _callFUT(self, *args, **kw):
        from guillotina.component import queryAdapter
        return queryAdapter(*args, **kw)

    def test_anonymous_nonesuch(self):
        from zope.interface import Interface
        class IFoo(Interface):
            pass
        self.assertEqual(self._callFUT(object(), IFoo, '', '<default>'),
                         '<default>')

    def test_named_nonesuch(self):
        from zope.interface import Interface
        class IFoo(Interface):
            pass
        self.assertEqual(self._callFUT(object(), IFoo, 'bar'), None)

    def test_anonymous_hit(self):
        from zope.interface import Interface
        from zope.interface import implementer
        from guillotina.component import getGlobalSiteManager
        class IFoo(Interface):
            pass
        class IBar(Interface):
            pass
        @implementer(IBar)
        class Bar(object):
            pass
        @implementer(IFoo)
        class Baz(object):
            def __init__(self, context):
                self.context = context
        getGlobalSiteManager().registerAdapter(Baz, (IBar,), IFoo, '')
        bar = Bar()
        adapted = self._callFUT(bar, IFoo, '')
        self.assertTrue(adapted.__class__ is Baz)
        self.assertTrue(adapted.context is bar)

    def test_named_hit(self):
        from zope.interface import Interface
        from zope.interface import implementer
        from guillotina.component import getGlobalSiteManager
        class IFoo(Interface):
            pass
        class IBar(Interface):
            pass
        @implementer(IBar)
        class Bar(object):
            pass
        @implementer(IFoo)
        class Baz(object):
            def __init__(self, context):
                self.context = context
        getGlobalSiteManager().registerAdapter(Baz, (IBar,), IFoo, 'named')
        bar = Bar()
        adapted = self._callFUT(bar, IFoo, 'named')
        self.assertTrue(adapted.__class__ is Baz)
        self.assertTrue(adapted.context is bar)

    def test_nested(self):
        from zope.interface import Interface
        from zope.interface import implementer
        from zope.interface.registry import Components
        from guillotina.component import getGlobalSiteManager
        from guillotina.component.tests.examples import ConformsToIComponentLookup
        class IFoo(Interface):
            pass
        class IBar(Interface):
            pass
        @implementer(IFoo)
        class Global(object):
            def __init__(self, context):
                self.context = context
        @implementer(IFoo)
        class Local(object):
            def __init__(self, context):
                self.context = context
        @implementer(IBar)
        class Bar(object):
            pass
        class Context(ConformsToIComponentLookup):
            def __init__(self, sm):
                self.sitemanager = sm
        gsm = getGlobalSiteManager()
        gsm.registerAdapter(Global, (IBar,), IFoo, '')
        sm1 = Components('sm1', bases=(gsm, ))
        sm1.registerAdapter(Local, (IBar,), IFoo, '')
        bar = Bar()
        adapted = self._callFUT(bar, IFoo, '', context=Context(sm1))
        self.assertTrue(adapted.__class__ is Local)
        self.assertTrue(adapted.context is bar)


class Test_getMultiAdapter(unittest.TestCase):

    from guillotina.component.testing import setUp, tearDown

    def _callFUT(self, *args, **kw):
        from guillotina.component import getMultiAdapter
        return getMultiAdapter(*args, **kw)

    def test_anonymous_nonesuch(self):
        from zope.interface import Interface
        from guillotina.component.interfaces import ComponentLookupError
        class IFoo(Interface):
            pass
        self.assertRaises(ComponentLookupError,
                          self._callFUT, (object(), object()), IFoo, '')

    def test_named_nonesuch(self):
        from zope.interface import Interface
        from guillotina.component.interfaces import ComponentLookupError
        class IFoo(Interface):
            pass
        self.assertRaises(ComponentLookupError,
                          self._callFUT, (object(), object()), IFoo, 'bar')

    def test_anonymous_hit(self):
        from zope.interface import Interface
        from zope.interface import implementer
        from guillotina.component import getGlobalSiteManager
        class IFoo(Interface):
            pass
        class IBar(Interface):
            pass
        class IBaz(Interface):
            pass
        @implementer(IBar)
        class Bar(object):
            pass
        @implementer(IBaz)
        class Baz(object):
            pass
        @implementer(IFoo)
        class FooAdapter(object):
            def __init__(self, first, second):
                self.first, self.second = first, second
        getGlobalSiteManager().registerAdapter(
                                FooAdapter, (IBar, IBaz), IFoo, '')
        bar = Bar()
        baz = Baz()
        adapted = self._callFUT((bar, baz), IFoo, '')
        self.assertTrue(adapted.__class__ is FooAdapter)
        self.assertTrue(adapted.first is bar)
        self.assertTrue(adapted.second is baz)

    def test_anonymous_hit_registered_for_None(self):
        from zope.interface import Interface
        from zope.interface import implementer
        from guillotina.component import getGlobalSiteManager
        class IFoo(Interface):
            pass
        class IBar(Interface):
            pass
        class IBaz(Interface):
            pass
        @implementer(IBar)
        class Bar(object):
            pass
        @implementer(IFoo)
        class FooAdapter(object):
            def __init__(self, first, second):
                self.first, self.second = first, second
        getGlobalSiteManager().registerAdapter(
                                FooAdapter, (IBar, None), IFoo, '')
        bar = Bar()
        baz = object()
        adapted = self._callFUT((bar, baz), IFoo, '')
        self.assertTrue(adapted.__class__ is FooAdapter)
        self.assertTrue(adapted.first is bar)
        self.assertTrue(adapted.second is baz)

    def test_named_hit(self):
        from zope.interface import Interface
        from zope.interface import implementer
        from guillotina.component import getGlobalSiteManager
        class IFoo(Interface):
            pass
        class IBar(Interface):
            pass
        class IBaz(Interface):
            pass
        @implementer(IBar)
        class Bar(object):
            pass
        @implementer(IBaz)
        class Baz(object):
            pass
        @implementer(IFoo)
        class FooAdapter(object):
            def __init__(self, first, second):
                self.first, self.second = first, second
        getGlobalSiteManager().registerAdapter(
                                    FooAdapter, (IBar, IBaz), IFoo, 'named')
        bar = Bar()
        baz = Baz()
        adapted = self._callFUT((bar, baz), IFoo, 'named')
        self.assertTrue(adapted.__class__ is FooAdapter)
        self.assertTrue(adapted.first is bar)
        self.assertTrue(adapted.second is baz)


class Test_queryMultiAdapter(unittest.TestCase):

    from guillotina.component.testing import setUp, tearDown

    def _callFUT(self, *args, **kw):
        from guillotina.component import queryMultiAdapter
        return queryMultiAdapter(*args, **kw)

    def test_anonymous_nonesuch(self):
        from zope.interface import Interface
        class IFoo(Interface):
            pass
        self.assertEqual(self._callFUT((object(), object()), IFoo, '',
                                            '<default>'),
                         '<default>')

    def test_named_nonesuch(self):
        from zope.interface import Interface
        class IFoo(Interface):
            pass
        self.assertEqual(self._callFUT((object(), object()), IFoo, 'bar'),
                         None)

    def test_anonymous_hit(self):
        from zope.interface import Interface
        from zope.interface import implementer
        from guillotina.component import getGlobalSiteManager
        class IFoo(Interface):
            pass
        class IBar(Interface):
            pass
        class IBaz(Interface):
            pass
        @implementer(IBar)
        class Bar(object):
            pass
        @implementer(IBaz)
        class Baz(object):
            pass
        @implementer(IFoo)
        class FooAdapter(object):
            def __init__(self, first, second):
                self.first, self.second = first, second
        getGlobalSiteManager().registerAdapter(
                                    FooAdapter, (IBar, IBaz), IFoo, '')
        bar = Bar()
        baz = Baz()
        adapted = self._callFUT((bar, baz), IFoo, '')
        self.assertTrue(adapted.__class__ is FooAdapter)
        self.assertTrue(adapted.first is bar)
        self.assertTrue(adapted.second is baz)

    def test_named_hit(self):
        from zope.interface import Interface
        from zope.interface import implementer
        from guillotina.component import getGlobalSiteManager
        class IFoo(Interface):
            pass
        class IBar(Interface):
            pass
        class IBaz(Interface):
            pass
        @implementer(IBar)
        class Bar(object):
            pass
        @implementer(IBaz)
        class Baz(object):
            pass
        @implementer(IFoo)
        class FooAdapter(object):
            def __init__(self, first, second):
                self.first, self.second = first, second
        getGlobalSiteManager().registerAdapter(
                                    FooAdapter, (IBar, IBaz), IFoo, 'named')
        bar = Bar()
        baz = Baz()
        adapted = self._callFUT((bar, baz), IFoo, 'named')
        self.assertTrue(adapted.__class__ is FooAdapter)
        self.assertTrue(adapted.first is bar)
        self.assertTrue(adapted.second is baz)

    def test_nested(self):
        from zope.interface import Interface
        from zope.interface import implementer
        from zope.interface.registry import Components
        from guillotina.component import getGlobalSiteManager
        from guillotina.component.tests.examples import ConformsToIComponentLookup
        class IFoo(Interface):
            pass
        class IBar(Interface):
            pass
        class IBaz(Interface):
            pass
        @implementer(IBar)
        class Bar(object):
            pass
        @implementer(IBaz)
        class Baz(object):
            pass
        @implementer(IFoo)
        class Global(object):
            def __init__(self, first, second):
                self.first, self.second = first, second
        @implementer(IFoo)
        class Local(object):
            def __init__(self, first, second):
                self.first, self.second = first, second
        class Context(ConformsToIComponentLookup):
            def __init__(self, sm):
                self.sitemanager = sm
        gsm = getGlobalSiteManager()
        gsm.registerAdapter(Global, (IBar, IBaz), IFoo, '')
        sm1 = Components('sm1', bases=(gsm, ))
        sm1.registerAdapter(Local, (IBar, IBaz), IFoo, '')
        bar = Bar()
        baz = Baz()
        adapted = self._callFUT((bar, baz), IFoo, '', context=Context(sm1))
        self.assertTrue(adapted.__class__ is Local)
        self.assertTrue(adapted.first is bar)
        self.assertTrue(adapted.second is baz)

    def test_wo_sitemanager(self):
        from zope.interface import Interface
        from zope.interface import implementer
        from guillotina.component.interfaces import ComponentLookupError
        class IFoo(Interface):
            pass
        class IBar(Interface):
            pass
        class IBaz(Interface):
            pass
        @implementer(IBar)
        class Bar(object):
            pass
        @implementer(IBaz)
        class Baz(object):
            pass
        class Context(object):
            def __conform__(self, iface):
                raise ComponentLookupError
        bar = Bar()
        baz = Baz()
        adapted = self._callFUT((bar, baz), IFoo, '', context=Context())
        self.assertTrue(adapted is None)


class Test_getAdapters(unittest.TestCase):

    from guillotina.component.testing import setUp, tearDown

    def _callFUT(self, *args, **kw):
        from guillotina.component import getAdapters
        return getAdapters(*args, **kw)

    def test_nonesuch(self):
        from zope.interface import Interface
        class IFoo(Interface):
            pass
        self.assertEqual(list(self._callFUT((object(),), IFoo)), [])

    def test_hit(self):
        from zope.interface import Interface
        from guillotina.component import getGlobalSiteManager
        class IFoo(Interface):
            pass
        class BarAdapter(object):
            def __init__(self, context):
                self.context = context
        class BazAdapter(object):
            def __init__(self, context):
                self.context = context
        gsm = getGlobalSiteManager()
        gsm.registerAdapter(BarAdapter, (None,), IFoo)
        gsm.registerAdapter(BazAdapter, (None,), IFoo, name='bar')
        tuples = list(self._callFUT((object(),), IFoo))
        self.assertEqual(len(tuples), 2)
        names = [(x, y.__class__.__name__) for x, y in tuples]
        self.assertTrue(('', 'BarAdapter') in names)
        self.assertTrue(('bar', 'BazAdapter') in names)

    def test_wo_sitemanager(self):
        from zope.interface import Interface
        from zope.interface import implementer
        from guillotina.component.interfaces import ComponentLookupError
        class IFoo(Interface):
            pass
        class IBar(Interface):
            pass
        class IBaz(Interface):
            pass
        @implementer(IBar)
        class Bar(object):
            pass
        @implementer(IBaz)
        class Baz(object):
            pass
        class Context(object):
            def __conform__(self, iface):
                raise ComponentLookupError
        bar = Bar()
        baz = Baz()
        adapted = self._callFUT((bar, baz), IFoo, context=Context())
        self.assertEqual(adapted, [])


class Test_subscribers(unittest.TestCase):

    from guillotina.component.testing import setUp, tearDown

    def _callFUT(self, *args, **kw):
        from guillotina.component import subscribers
        return subscribers(*args, **kw)

    def test_nonesuch(self):
        from zope.interface import Interface
        class IFoo(Interface):
            pass
        subscribers = self._callFUT((object,), IFoo)
        self.assertEqual(subscribers, [])

    def test_hit(self):
        from zope.interface import Interface
        from guillotina.component import getGlobalSiteManager
        class IFoo(Interface):
            pass
        class BarAdapter(object):
            def __init__(self, context):
                self.context = context
        class BazAdapter(object):
            def __init__(self, context):
                self.context = context
        gsm = getGlobalSiteManager()
        gsm.registerSubscriptionAdapter(BarAdapter, (None,), IFoo)
        gsm.registerSubscriptionAdapter(BazAdapter, (None,), IFoo)
        subscribers = self._callFUT((object(),), IFoo)
        self.assertEqual(len(subscribers), 2)
        names = [(x.__class__.__name__) for x in subscribers]
        self.assertTrue('BarAdapter' in names)
        self.assertTrue('BazAdapter' in names)

    def test_wo_sitemanager(self):
        from zope.interface import Interface
        from guillotina.component.interfaces import ComponentLookupError
        class IFoo(Interface):
            pass
        class Context(object):
            def __conform__(self, iface):
                raise ComponentLookupError
        subscribers = self._callFUT((object,), IFoo, context=Context())
        self.assertEqual(subscribers, [])


class Test_handle(unittest.TestCase):

    from guillotina.component.testing import setUp, tearDown

    def _callFUT(self, *args, **kw):
        from guillotina.component import handle
        return handle(*args, **kw)

    def test_nonesuch(self):
        from zope.interface import Interface
        class IFoo(Interface):
            pass
        subscribers = self._callFUT((object,), IFoo) #doesn't raise

    def test_hit(self):
        from guillotina.component import getGlobalSiteManager
        from zope.interface import Interface
        from zope.interface import implementer
        class IFoo(Interface):
            pass
        @implementer(IFoo)
        class Foo(object):
            pass
        _called = []
        def _bar(context):
                _called.append('_bar')
        def _baz(context):
                _called.append('_baz')
        gsm = getGlobalSiteManager()
        gsm.registerHandler(_bar, (IFoo,))
        gsm.registerHandler(_baz, (IFoo,))
        self._callFUT(Foo())
        self.assertEqual(len(_called), 2, _called)
        self.assertTrue('_bar' in _called)
        self.assertTrue('_baz' in _called)


class Test_getUtility(unittest.TestCase):

    from guillotina.component.testing import setUp, tearDown

    def _callFUT(self, *args, **kw):
        from guillotina.component._api import getUtility
        return getUtility(*args, **kw)

    def test_anonymous_nonesuch(self):
        from zope.interface import Interface
        from guillotina.component.interfaces import ComponentLookupError
        class IFoo(Interface):
            pass
        self.assertRaises(ComponentLookupError, self._callFUT, IFoo)

    def test_named_nonesuch(self):
        from zope.interface import Interface
        from guillotina.component.interfaces import ComponentLookupError
        class IFoo(Interface):
            pass
        self.assertRaises(ComponentLookupError,
                          self._callFUT, IFoo, name='bar')

    def test_anonymous_hit(self):
        from zope.interface import Interface
        from guillotina.component import getGlobalSiteManager
        class IFoo(Interface):
            pass
        obj = object()
        getGlobalSiteManager().registerUtility(obj, IFoo)
        self.assertTrue(self._callFUT(IFoo) is obj)

    def test_named_hit(self):
        from zope.interface import Interface
        from guillotina.component import getGlobalSiteManager
        class IFoo(Interface):
            pass
        obj = object()
        getGlobalSiteManager().registerUtility(obj, IFoo, name='bar')
        self.assertTrue(self._callFUT(IFoo, name='bar') is obj)

    def test_w_conforming_context(self):
        from zope.interface import Interface
        from guillotina.component import getGlobalSiteManager
        from guillotina.component.tests.examples import ConformsToIComponentLookup
        class SM(object):
            def __init__(self, obj):
                self._obj = obj
            def queryUtility(self, interface, name, default):
                return self._obj
        class IFoo(Interface):
            pass
        obj1 = object()
        obj2 = object()
        sm = SM(obj2)
        context = ConformsToIComponentLookup(sm)
        getGlobalSiteManager().registerUtility(obj1, IFoo)
        self.assertTrue(self._callFUT(IFoo, context=context) is obj2)


class Test_queryUtility(unittest.TestCase):

    from guillotina.component.testing import setUp, tearDown

    def _callFUT(self, *args, **kw):
        from guillotina.component._api import queryUtility
        return queryUtility(*args, **kw)

    def test_anonymous_nonesuch(self):
        from zope.interface import Interface
        class IFoo(Interface):
            pass
        self.assertEqual(self._callFUT(IFoo), None)

    def test_anonymous_nonesuch_w_default(self):
        from zope.interface import Interface
        class IFoo(Interface):
            pass
        obj = object()
        self.assertTrue(self._callFUT(IFoo, default=obj) is obj)

    def test_named_nonesuch(self):
        from zope.interface import Interface
        class IFoo(Interface):
            pass
        self.assertEqual(self._callFUT(IFoo, name='bar'), None)

    def test_named_nonesuch_w_default(self):
        from zope.interface import Interface
        class IFoo(Interface):
            pass
        obj = object()
        self.assertTrue(self._callFUT(IFoo, name='bar', default=obj) is obj)

    def test_anonymous_hit(self):
        from zope.interface import Interface
        from guillotina.component import getGlobalSiteManager
        class IFoo(Interface):
            pass
        obj = object()
        getGlobalSiteManager().registerUtility(obj, IFoo)
        self.assertTrue(self._callFUT(IFoo) is obj)

    def test_named_hit(self):
        from zope.interface import Interface
        from guillotina.component import getGlobalSiteManager
        class IFoo(Interface):
            pass
        obj = object()
        getGlobalSiteManager().registerUtility(obj, IFoo, name='bar')
        self.assertTrue(self._callFUT(IFoo, name='bar') is obj)

    def test_w_conforming_context(self):
        from zope.interface import Interface
        from guillotina.component import getGlobalSiteManager
        from guillotina.component.tests.examples import ConformsToIComponentLookup
        class SM(object):
            def __init__(self, obj):
                self._obj = obj
            def queryUtility(self, interface, name, default):
                return self._obj
        class IFoo(Interface):
            pass
        obj1 = object()
        obj2 = object()
        sm = SM(obj2)
        context = ConformsToIComponentLookup(sm)
        getGlobalSiteManager().registerUtility(obj1, IFoo)
        self.assertTrue(self._callFUT(IFoo, context=context) is obj2)


class Test_getUtilitiesFor(unittest.TestCase):

    from guillotina.component.testing import setUp, tearDown

    def _callFUT(self, *args, **kw):
        from guillotina.component._api import getUtilitiesFor
        return getUtilitiesFor(*args, **kw)

    def test_nonesuch(self):
        from zope.interface import Interface
        class IFoo(Interface):
            pass
        self.assertEqual(list(self._callFUT(IFoo)), [])

    def test_hit(self):
        from zope.interface import Interface
        from guillotina.component import getGlobalSiteManager
        class IFoo(Interface):
            pass
        obj = object()
        obj1 = object()
        getGlobalSiteManager().registerUtility(obj, IFoo)
        getGlobalSiteManager().registerUtility(obj1, IFoo, name='bar')
        tuples = list(self._callFUT(IFoo))
        self.assertEqual(len(tuples), 2)
        self.assertTrue(('', obj) in tuples)
        self.assertTrue(('bar', obj1) in tuples)


class Test_getAllUtilitiesRegisteredFor(unittest.TestCase):

    from guillotina.component.testing import setUp, tearDown

    def _callFUT(self, *args, **kw):
        from guillotina.component import getAllUtilitiesRegisteredFor
        return getAllUtilitiesRegisteredFor(*args, **kw)

    def test_nonesuch(self):
        from zope.interface import Interface
        class IFoo(Interface):
            pass
        self.assertEqual(list(self._callFUT(IFoo)), [])

    def test_hit(self):
        from zope.interface import Interface
        from guillotina.component import getGlobalSiteManager
        class IFoo(Interface):
            pass
        class IBar(IFoo):
            pass
        obj = object()
        obj1 = object()
        obj2 = object()
        getGlobalSiteManager().registerUtility(obj, IFoo)
        getGlobalSiteManager().registerUtility(obj1, IFoo, name='bar')
        getGlobalSiteManager().registerUtility(obj2, IBar)
        uts = list(self._callFUT(IFoo))
        self.assertEqual(len(uts), 3)
        self.assertTrue(obj in uts)
        self.assertTrue(obj1 in uts)
        self.assertTrue(obj2 in uts)


class Test_getFactoryInterfaces(unittest.TestCase):

    from guillotina.component.testing import setUp, tearDown

    def _callFUT(self, *args, **kw):
        from guillotina.component import getFactoryInterfaces
        return getFactoryInterfaces(*args, **kw)

    def test_miss(self):
        from guillotina.component.interfaces import ComponentLookupError
        self.assertRaises(ComponentLookupError, self._callFUT, 'nonesuch')

    def test_hit(self):
        from guillotina.component.interfaces import IFactory
        from zope.interface import Interface
        class IFoo(Interface):
            pass
        class _Factory(object):
            def get_interfaces(self):
                return [IFoo]
        class Context(object):
            def __conform__(self, iface):
                return self
            def queryUtility(self, iface, name, default):
                if iface is IFactory and name == 'test':
                    return _Factory()
                return default
        context = Context()
        self.assertEqual(self._callFUT('test', context=context), [IFoo])


class Test_getFactoriesFor(unittest.TestCase):

    from guillotina.component.testing import setUp, tearDown

    def _callFUT(self, *args, **kw):
        from guillotina.component import getFactoriesFor
        return getFactoriesFor(*args, **kw)

    def test_no_factories_registered(self):
        from zope.interface import Interface
        class IFoo(Interface):
            pass
        self.assertEqual(list(self._callFUT(IFoo)), [])

    def test_w_factory_returning_spec(self):
        from zope.interface import Interface
        from zope.interface import implementer
        from zope.interface import providedBy
        from guillotina.component.interfaces import IFactory
        class IFoo(Interface):
            pass
        class IBar(Interface):
            pass
        @implementer(IFoo, IBar)
        class _Factory(object):
            def get_interfaces(self):
                return providedBy(self)
        _factory = _Factory()
        class Context(object):
            def __conform__(self, iface):
                return self
            def getUtilitiesFor(self, iface):
                if iface is IFactory:
                    return [('test', _factory)]
        self.assertEqual(list(self._callFUT(IFoo, context=Context())),
                         [('test', _factory)])
        self.assertEqual(list(self._callFUT(IBar, context=Context())),
                         [('test', _factory)])

    def test_w_factory_returning_list_of_interfaces(self):
        from zope.interface import Interface
        from guillotina.component.interfaces import IFactory
        class IFoo(Interface):
            pass
        class IBar(Interface):
            pass
        class _Factory(object):
            def get_interfaces(self):
                return [IFoo, IBar]
        _factory = _Factory()
        class Context(object):
            def __conform__(self, iface):
                return self
            def getUtilitiesFor(self, iface):
                if iface is IFactory:
                    return [('test', _factory)]
        self.assertEqual(list(self._callFUT(IFoo, context=Context())),
                         [('test', _factory)])
        self.assertEqual(list(self._callFUT(IBar, context=Context())),
                         [('test', _factory)])


IMyUtility = None
def _makeMyUtility(name, sm):
    global IMyUtility
    from zope.interface import Interface
    from zope.interface import implementer
    from guillotina.component.tests.examples import ConformsToIComponentLookup

    if IMyUtility is None:
        class IMyUtility(Interface):
            pass

    @implementer(IMyUtility)
    class MyUtility(ConformsToIComponentLookup):
        def __init__(self, id, sm):
            self.id = id
            self.sitemanager = sm

    return MyUtility(name, sm)


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(Test_getSiteManager),
        unittest.makeSuite(Test_getAdapterInContext),
        unittest.makeSuite(Test_queryAdapterInContext),
        unittest.makeSuite(Test_getAdapter),
        unittest.makeSuite(Test_queryAdapter),
        unittest.makeSuite(Test_getMultiAdapter),
        unittest.makeSuite(Test_queryMultiAdapter),
        unittest.makeSuite(Test_getAdapters),
        unittest.makeSuite(Test_subscribers),
        unittest.makeSuite(Test_handle),
        unittest.makeSuite(Test_getUtility),
        unittest.makeSuite(Test_queryUtility),
        unittest.makeSuite(Test_getUtilitiesFor),
        unittest.makeSuite(Test_getAllUtilitiesRegisteredFor),
        unittest.makeSuite(Test_getFactoryInterfaces),
        unittest.makeSuite(Test_getFactoriesFor),
    ))

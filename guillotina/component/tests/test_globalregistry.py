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

class Test_get_global_components(unittest.TestCase):

    def _callFUT(self):
        from guillotina.component.globalregistry import get_global_components
        return get_global_components()

    def test_gsm_is_IComponentLookup(self):
        from guillotina.component.globalregistry import base
        from guillotina.component.interfaces import IComponentLookup
        gsm = self._callFUT()
        self.assertTrue(gsm is base)
        self.assertTrue(IComponentLookup.providedBy(gsm))

    def test_gsm_is_singleton(self):
        gsm = self._callFUT()


class Test_provide_utility(unittest.TestCase):

    from guillotina.component.testing import setUp, tearDown

    def _callFUT(self, *args, **kw):
        from guillotina.component.globalregistry import provide_utility
        return provide_utility(*args, **kw)

    def test_anonymous_no_provides(self):
        from zope.interface import Interface
        from zope.interface import implementer
        from guillotina.component.globalregistry import get_global_components
        class IFoo(Interface):
            pass
        @implementer(IFoo)
        class Foo(object):
            pass
        foo = Foo()
        self._callFUT(foo)
        gsm = get_global_components()
        self.assertTrue(gsm.getUtility(IFoo, '') is foo)

    def test_named_w_provides(self):
        from zope.interface import Interface
        from guillotina.component.globalregistry import get_global_components
        class IFoo(Interface):
            pass
        class Foo(object):
            pass
        foo = Foo()
        self._callFUT(foo, IFoo, 'named')
        gsm = get_global_components()
        self.assertTrue(gsm.getUtility(IFoo, 'named') is foo)


class Test_provide_adapter(unittest.TestCase):

    from guillotina.component.testing import setUp, tearDown

    def _callFUT(self, *args, **kw):
        from guillotina.component.globalregistry import provide_adapter
        return provide_adapter(*args, **kw)

    def test_anonymous_no_provides_no_adapts(self):
        from zope.interface import Interface
        from zope.interface import implementer
        from guillotina.component.globalregistry import get_global_components
        from guillotina.component._declaration import adapter
        class IFoo(Interface):
            pass
        class IBar(Interface):
            pass
        @implementer(IFoo)
        class Foo(object):
            pass
        @adapter(IFoo)
        @implementer(IBar)
        class Bar(object):
            def __init__(self, context):
                self.context = context
        self._callFUT(Bar)
        gsm = get_global_components()
        foo = Foo()
        adapted = gsm.getAdapter(foo, IBar)
        self.assertTrue(isinstance(adapted, Bar))
        self.assertTrue(adapted.context is foo)

    def test_named_w_provides_w_adapts(self):
        from zope.interface import Interface
        from zope.interface import implementer
        from guillotina.component.globalregistry import get_global_components
        class IFoo(Interface):
            pass
        class IBar(Interface):
            pass
        @implementer(IFoo)
        class Foo(object):
            pass
        class Bar(object):
            def __init__(self, context):
                self.context = context
        self._callFUT(Bar, (IFoo,), IBar, 'test')
        gsm = get_global_components()
        foo = Foo()
        adapted = gsm.getAdapter(foo, IBar, name='test')
        self.assertTrue(isinstance(adapted, Bar))
        self.assertTrue(adapted.context is foo)


class Test_provide_subscription_adapter(unittest.TestCase):

    from guillotina.component.testing import setUp, tearDown

    def _callFUT(self, *args, **kw):
        from guillotina.component.globalregistry import provide_subscription_adapter
        return provide_subscription_adapter(*args, **kw)

    def test_no_provides_no_adapts(self):
        from zope.interface import Interface
        from zope.interface import implementer
        from guillotina.component.globalregistry import get_global_components
        from guillotina.component._declaration import adapter
        class IFoo(Interface):
            pass
        class IBar(Interface):
            pass
        @implementer(IFoo)
        class Foo(object):
            pass
        @adapter(IFoo)
        @implementer(IBar)
        class Bar(object):
            def __init__(self, context):
                self.context = context
        self._callFUT(Bar)
        gsm = get_global_components()
        foo = Foo()
        adapted = gsm.subscribers((foo,), IBar)
        self.assertEqual(len(adapted), 1)
        self.assertTrue(isinstance(adapted[0], Bar))
        self.assertTrue(adapted[0].context is foo)

    def test_w_provides_w_adapts(self):
        from zope.interface import Interface
        from zope.interface import implementer
        from guillotina.component.globalregistry import get_global_components
        class IFoo(Interface):
            pass
        class IBar(Interface):
            pass
        @implementer(IFoo)
        class Foo(object):
            pass
        class Bar(object):
            def __init__(self, context):
                self.context = context
        self._callFUT(Bar, (IFoo,), IBar)
        gsm = get_global_components()
        foo = Foo()
        adapted = gsm.subscribers((foo,), IBar)
        self.assertEqual(len(adapted), 1)
        self.assertTrue(isinstance(adapted[0], Bar))
        self.assertTrue(adapted[0].context is foo)


class Test_provide_handler(unittest.TestCase):

    from guillotina.component.testing import setUp, tearDown

    def _callFUT(self, *args, **kw):
        from guillotina.component.globalregistry import provide_handler
        return provide_handler(*args, **kw)

    def test_no_adapts(self):
        from zope.interface import Interface
        from zope.interface import implementer
        from zope.interface import providedBy
        from guillotina.component.globalregistry import get_global_components
        from guillotina.component._declaration import adapter
        class IFoo(Interface):
            pass
        @implementer(IFoo)
        class Foo(object):
            pass
        @adapter(IFoo)
        def _handler(context):
            assert 0, "DON'T GO HERE"
        self._callFUT(_handler)
        gsm = get_global_components()
        regs = list(gsm.registeredHandlers())
        self.assertEqual(len(regs), 1)
        hr = regs[0]
        self.assertEqual(list(hr.required), list(providedBy(Foo())))
        self.assertEqual(hr.name, '')
        self.assertTrue(hr.factory is _handler)

    def test_w_adapts(self):
        from zope.interface import Interface
        from guillotina.component.globalregistry import get_global_components
        class IFoo(Interface):
            pass
        def _handler(context):
            assert 0, "DON'T GO HERE"
        self._callFUT(_handler, (IFoo,))
        gsm = get_global_components()
        regs = list(gsm.registeredHandlers())
        self.assertEqual(len(regs), 1)
        hr = regs[0]
        self.assertEqual(list(hr.required), [IFoo])
        self.assertEqual(hr.name, '')
        self.assertTrue(hr.factory is _handler)


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(Test_get_global_components),
        unittest.makeSuite(Test_provide_utility),
        unittest.makeSuite(Test_provide_adapter),
        unittest.makeSuite(Test_provide_subscription_adapter),
        unittest.makeSuite(Test_provide_handler),
    ))

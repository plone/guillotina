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


class HookableTests(unittest.TestCase):
    def test_ctor_no_func(self):
        from guillotina.component.hookable import hookable

        self.assertRaises(TypeError, hookable)

    def test_ctor_simple(self):
        from guillotina.component.hookable import hookable

        def foo():
            pass

        hooked = hookable(foo)
        self.assertTrue(hooked.original is foo)
        self.assertTrue(hooked.implementation is foo)

    def test_ctor_extra_arg(self):
        from guillotina.component.hookable import hookable

        def foo():
            pass

        self.assertRaises(TypeError, hookable, foo, foo)

    def test_ctor_extra_arg_miss(self):
        from guillotina.component.hookable import hookable

        def foo():
            pass

        self.assertRaises(TypeError, hookable, foo, nonesuch=foo)

    def test_sethook(self):
        from guillotina.component.hookable import hookable

        def foo():
            pass

        def bar():
            pass

        hooked = hookable(foo)
        hooked.sethook(bar)
        self.assertTrue(hooked.original is foo)
        self.assertTrue(hooked.implementation is bar)

    def test_reset(self):
        from guillotina.component.hookable import hookable

        def foo():
            pass

        def bar():
            pass

        hooked = hookable(foo)
        hooked.sethook(bar)
        hooked.reset()
        self.assertTrue(hooked.original is foo)
        self.assertTrue(hooked.implementation is foo)

    def test_cant_assign_original(self):
        from guillotina.component.hookable import hookable

        def foo():
            pass

        def bar():
            pass

        hooked = hookable(foo)
        try:
            hooked.original = bar
        except TypeError:
            pass
        except AttributeError:
            pass
        else:
            self.fail("Assigned original")

    def test_cant_delete_original(self):
        from guillotina.component.hookable import hookable

        def foo():
            pass

        hooked = hookable(foo)
        try:
            del hooked.original
        except TypeError:
            pass
        except AttributeError:
            pass
        else:
            self.fail("Deleted original")

    def test_cant_assign_implementation(self):
        from guillotina.component.hookable import hookable

        def foo():
            pass

        def bar():
            pass

        hooked = hookable(foo)
        try:
            hooked.implementation = bar
        except TypeError:
            pass
        except AttributeError:
            pass
        else:
            self.fail("Assigned implementation")

    def test_cant_delete_implementation(self):
        from guillotina.component.hookable import hookable

        def foo():
            pass

        hooked = hookable(foo)
        try:
            del hooked.implementation
        except TypeError:
            pass
        except AttributeError:
            pass
        else:
            self.fail("Deleted implementation")

    def test_ctor___call__(self):
        from guillotina.component.hookable import hookable

        _called = []

        def foo(*args, **kw):
            _called.append((args, kw))

        hooked = hookable(foo)
        hooked("one", "two", bar="baz")
        self.assertEqual(_called, [(("one", "two"), {"bar": "baz"})])


def test_suite():
    return unittest.TestSuite((unittest.makeSuite(HookableTests),))

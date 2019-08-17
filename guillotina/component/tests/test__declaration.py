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


class Test_adapter(unittest.TestCase):
    def _getTargetClass(self):
        from guillotina.component._declaration import adapter

        return adapter

    def _makeOne(self, *interfaces):
        return self._getTargetClass()(*interfaces)

    def test_ctor_no_interfaces(self):
        deco = self._makeOne()
        self.assertEqual(list(deco.interfaces), [])

    def test_ctor_w_interfaces(self):
        from zope.interface import Interface

        class IFoo(Interface):
            pass

        class IBar(Interface):
            pass

        deco = self._makeOne(IFoo, IBar)
        self.assertEqual(list(deco.interfaces), [IFoo, IBar])

    def test__call___w_class(self):
        from zope.interface import Interface

        class IFoo(Interface):
            pass

        class IBar(Interface):
            pass

        @self._makeOne(IFoo, IBar)
        class Baz(object):
            pass

        self.assertEqual(Baz.__component_adapts__, (IFoo, IBar))

    def test__call___w_inst_of_decorated_class(self):
        from zope.interface import Interface

        class IFoo(Interface):
            pass

        class IBar(Interface):
            pass

        @self._makeOne(IFoo, IBar)
        class Baz(object):
            pass

        baz = Baz()
        self.assertRaises(AttributeError, getattr, baz, "__component_adapts_")

    def test__call___w_non_class(self):
        from zope.interface import Interface

        class IFoo(Interface):
            pass

        class IBar(Interface):
            pass

        class Baz(object):
            pass

        deco = self._makeOne(IFoo, IBar)
        baz = deco(Baz())
        self.assertEqual(baz.__component_adapts__, (IFoo, IBar))


class Test_adapts(unittest.TestCase):
    def _run_generated_code(self, code, globs, locs, fails_under_py3k=True):
        import warnings

        # from guillotina.component._compat import PYTHON3
        PYTHON3 = False
        with warnings.catch_warnings(record=True) as log:
            warnings.resetwarnings()
            if not PYTHON3:
                exec(code, globs, locs)
                self.assertEqual(len(log), 0)  # no longer warn
                return True
            else:
                try:
                    exec(code, globs, locs)
                except TypeError:
                    return False
                else:
                    if fails_under_py3k:
                        self.fail("Didn't raise TypeError")

    def test_instances_not_affected(self):
        from guillotina.component._declaration import adapts

        class C(object):
            adapts()

        self.assertEqual(C.__component_adapts__, ())

        def _try():
            return C().__component_adapts__

        self.assertRaises(AttributeError, _try)

    def test_called_from_function(self):
        import warnings
        from guillotina.component._declaration import adapts
        from zope.interface import Interface

        class IFoo(Interface):
            pass

        globs = {"adapts": adapts, "IFoo": IFoo}
        locs = {}
        CODE = "\n".join(["def foo():", "    adapts(IFoo)"])
        if self._run_generated_code(CODE, globs, locs, False):
            foo = locs["foo"]
            with warnings.catch_warnings(record=True) as log:
                warnings.resetwarnings()
                self.assertRaises(TypeError, foo)
                self.assertEqual(len(log), 0)  # no longer warn

    def test_called_twice_from_class(self):
        import warnings
        from guillotina.component._declaration import adapts
        from zope.interface import Interface
        from zope.interface._compat import PYTHON3

        class IFoo(Interface):
            pass

        class IBar(Interface):
            pass

        globs = {"adapts": adapts, "IFoo": IFoo, "IBar": IBar}
        locs = {}
        CODE = "\n".join(["class Foo(object):", "    adapts(IFoo)", "    adapts(IBar)"])
        with warnings.catch_warnings(record=True) as log:
            warnings.resetwarnings()
            try:
                exec(CODE, globs, locs)
            except TypeError:
                if not PYTHON3:
                    self.assertEqual(len(log), 0)  # no longer warn
            else:
                self.fail("Didn't raise TypeError")

    def test_called_once_from_class(self):
        from guillotina.component._declaration import adapts
        from zope.interface import Interface

        class IFoo(Interface):
            pass

        globs = {"adapts": adapts, "IFoo": IFoo}
        locs = {}
        CODE = "\n".join(["class Foo(object):", "    adapts(IFoo)"])
        if self._run_generated_code(CODE, globs, locs):
            Foo = locs["Foo"]
            spec = Foo.__component_adapts__
            self.assertEqual(list(spec), [IFoo])


class Test_adaptedBy(unittest.TestCase):
    def _callFUT(self, obj):
        from guillotina.component._declaration import adaptedBy

        return adaptedBy(obj)

    def test_obj_w_no_attr(self):
        self.assertEqual(self._callFUT(object()), None)

    def test__call___w_class(self):
        from zope.interface import Interface

        class IFoo(Interface):
            pass

        class IBar(Interface):
            pass

        class Baz(object):
            __component_adapts__ = (IFoo, IBar)

        self.assertEqual(self._callFUT(Baz), (IFoo, IBar))

    def test__call___w_inst_of_decorated_class(self):
        from zope.interface import Interface
        from guillotina.component._declaration import _adapts_descr

        class IFoo(Interface):
            pass

        class IBar(Interface):
            pass

        class Baz(object):
            __component_adapts__ = _adapts_descr((IFoo, IBar))

        baz = Baz()
        self.assertEqual(self._callFUT(baz), None)

    def test__call___w_non_class(self):
        from zope.interface import Interface

        class IFoo(Interface):
            pass

        class IBar(Interface):
            pass

        class Baz(object):
            pass

        baz = Baz()
        baz.__component_adapts__ = (IFoo, IBar)
        self.assertEqual(self._callFUT(baz), (IFoo, IBar))


def test_suite():
    return unittest.TestSuite(
        (
            unittest.makeSuite(Test_adapter),
            unittest.makeSuite(Test_adapts),
            unittest.makeSuite(Test_adaptedBy),
        )
    )

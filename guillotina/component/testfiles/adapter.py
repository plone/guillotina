##############################################################################
#
# Copyright (c) 2004 Zope Foundation and Contributors.
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

from guillotina.component import adapter
from guillotina.component.testfiles import components
from zope.interface import implementer
from zope.interface import Interface


class I1(Interface):
    pass


class I2(Interface):
    pass


class I3(Interface):
    def f1():
        pass  # type: ignore

    def f2():
        pass  # type: ignore

    def f3():
        pass  # type: ignore


class IS(Interface):
    pass


class Adapter(object):
    def __init__(self, *args):
        self.context = args


@implementer(I1)
class A1(Adapter):
    pass


@implementer(I2)
class A2(Adapter):
    pass


@adapter(components.IContent, I1, I2)
@implementer(I3)
class A3(Adapter):  # type: ignore
    pass


class A4:
    pass


a4 = A4()


@implementer(I1, I2)
class A5:  # type: ignore
    """ """


a5 = A5()


def Handler(content, *args):
    # uninteresting handler
    content.args = getattr(content, "args", ()) + (args,)

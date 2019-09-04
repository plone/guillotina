##############################################################################
#
# Copyright (c) 2002 Zope Foundation and Contributors.
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
from zope.interface import Attribute
from zope.interface import implementer
from zope.interface import Interface
from zope.interface import named


class IAppb(Interface):
    a = Attribute("test attribute")

    def f():
        "test func"  # type: ignore


class IApp(IAppb):
    pass


class IApp2(IAppb):
    pass


class IApp3(IAppb):
    pass


class IContent(Interface):
    pass


@implementer(IContent)
class Content(object):
    pass


@adapter(IContent)
@implementer(IApp)
class Comp(object):
    def __init__(self, *args):
        # Ignore arguments passed to constructor
        pass

    a = 1

    def f(self):
        pass  # type: ignore


class Comp2(object):
    def __init__(self, context):
        self.context = context


class Comp3(object):
    def __init__(self, context):
        self.context = context


@adapter(IContent)
@implementer(IApp)
@named("app")
class Comp4(object):  # type: ignore
    def __init__(self, context=None):
        self.context = context


comp = Comp()
comp4 = Comp4()  # type: ignore

content = Content()

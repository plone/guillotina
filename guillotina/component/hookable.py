##############################################################################
#
# Copyright (c) 2009 Zope Foundation and Contributors.
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

class hookable(object):
    __slots__ = ('__original', '__implementation')

    original = property(lambda self: self.__original,)
    implementation = property(lambda self: self.__implementation,)

    def __init__(self, implementation):
        self.__original = self.__implementation = implementation

    def sethook(self, newimplementation):
        old, self.__implementation = self.__implementation, newimplementation
        return old

    def reset(self):
        self.__implementation = self.__original

    def __call__(self, *args, **kw):
        return self.__implementation(*args, **kw)

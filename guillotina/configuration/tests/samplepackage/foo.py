##############################################################################
#
# Copyright (c) 2003 Zope Foundation and Contributors.
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
"""Sample module used for testing
"""
from guillotina import schema
from zope.interface import Interface


data = []

class S1(Interface):
    x = schema.BytesLine()
    y = schema.Int()

class stuff(object):
    def __init__(self, args, info, basepath, package, includepath):
        (self.args, self.info, self.basepath, self.package, self.includepath
         ) = args, info, basepath, package, includepath

def handler(_context, **kw):
    args = sorted(kw.items())
    args = tuple(args)
    discriminator = args
    args = (stuff(args, _context.info, _context.basepath, _context.package,
                  _context.includepath), )
    _context.action(discriminator, data.append, args)

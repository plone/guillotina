##############################################################################
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
##############################################################################
# flake8: noqa

from zope.interface import Interface
from zope.interface import implementer
from zope.interface import directlyProvides

class Request(object):

    def __init__(self, type):
        directlyProvides(self, type)

class IR(Interface):
    pass

class IV(Interface):
    def index():  # type: ignore
        pass

class IC(Interface): pass

@implementer(IV)
class V1(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def index(self):
        return 'V1 here'

    def action(self):
        return 'done'

class VZMI(V1):
    def index(self):
        return 'ZMI here'

@implementer(IV)
class R1(object):

    def index(self):
        return 'R1 here'

    def action(self):
        return 'R done'

    def __init__(self, request):
        pass


class RZMI(R1):
    pass

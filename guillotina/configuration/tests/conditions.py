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
""" Enable "Making specific directives condition" section of narrative docs.
"""
from zope.interface import Interface
from guillotina.schema import Id

from guillotina.configuration._compat import u


class IRegister(Interface):
    """Trivial sample registry."""

    id = Id(
        title=u("Identifier"),
        description=u("Some identifier that can be checked."),
        required=True,
        )

registry = []

def register(context, id):
    context.action(discriminator=('Register', id),
                   callable=registry.append,
                   args=(id,)
                   )

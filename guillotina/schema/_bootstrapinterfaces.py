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
import zope.interface


class IFromUnicode(zope.interface.Interface):
    """Parse a unicode string to a value

    We will often adapt fields to this interface to support views and
    other applications that need to conver raw data as unicode
    values.
    """

    def from_unicode(str):
        """Convert a unicode string to a value.
        """


class IContextAwareDefaultFactory(zope.interface.Interface):
    """A default factory that requires a context.

    The context is the field context. If the field is not bound, context may
    be ``None``.
    """

    def __call__(context):
        """Returns a default value for the field."""


class _NO_VALUE(object):
    def __repr__(self):
        return '<NO_VALUE>'


NO_VALUE = _NO_VALUE()

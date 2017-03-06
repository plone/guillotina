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
"""Configuration-specific schema fields
"""
from guillotina.configuration._compat import u
from guillotina.configuration.exceptions import ConfigurationError
from guillotina.configuration.interfaces import InvalidToken
from guillotina.schema import Bool as schema_Bool
from guillotina.schema import Field
from guillotina.schema import InterfaceField
from guillotina.schema import List
from guillotina.schema import Text
from guillotina.schema import TextLine
from guillotina.schema import ValidationError
from guillotina.schema.interfaces import IFromUnicode
from zope.interface import implementer

import os
import re
import warnings


PYIDENTIFIER_REGEX = u('\\A[a-zA-Z_]+[a-zA-Z0-9_]*\\Z')
pyidentifierPattern = re.compile(PYIDENTIFIER_REGEX)


@implementer(IFromUnicode)
class PythonIdentifier(TextLine):
    """This field describes a python identifier, i.e. a variable name.
    """
    def fromUnicode(self, u):
        return u.strip()

    def _validate(self, value):
        super(PythonIdentifier, self)._validate(value)
        if pyidentifierPattern.match(value) is None:
            raise ValidationError(value)


@implementer(IFromUnicode)
class GlobalObject(Field):
    """An object that can be accessed as a module global.
    """
    def __init__(self, value_type=None, **kw):
        self.value_type = value_type
        super(GlobalObject, self).__init__(**kw)

    def _validate(self, value):
        super(GlobalObject, self)._validate(value)
        if self.value_type is not None:
            self.value_type.validate(value)

    def fromUnicode(self, u):
        name = str(u.strip())

        # special case, mostly for interfaces
        if name == '*':
            return None

        try:
            value = self.context.resolve(name)
        except ConfigurationError as v:
            raise ValidationError(v)

        self.validate(value)
        return value


@implementer(IFromUnicode)
class GlobalInterface(GlobalObject):
    """An interface that can be accessed from a module.
    """
    def __init__(self, **kw):
        super(GlobalInterface, self).__init__(InterfaceField(), **kw)


@implementer(IFromUnicode)
class Tokens(List):
    """A list that can be read from a space-separated string.
    """
    def fromUnicode(self, u):
        u = u.strip()
        if u:
            vt = self.value_type.bind(self.context)
            values = []
            for s in u.split():
                try:
                    v = vt.fromUnicode(s)
                except ValidationError as v:
                    raise InvalidToken("%s in %s" % (v, u))
                else:
                    values.append(v)
        else:
            values = []

        self.validate(values)

        return values


@implementer(IFromUnicode)
class Path(Text):
    """A file path name, which may be input as a relative path

    Input paths are converted to absolute paths and normalized.
    """
    def fromUnicode(self, u):
        u = u.strip()
        if os.path.isabs(u):
            return os.path.normpath(u)

        return self.context.path(u)


@implementer(IFromUnicode)
class Bool(schema_Bool):
    """A boolean value

    Values may be input (in upper or lower case) as any of:
       yes, no, y, n, true, false, t, or f.
    """
    def fromUnicode(self, u):
        u = u.lower()
        if u in ('1', 'true', 'yes', 't', 'y'):
            return True
        if u in ('0', 'false', 'no', 'f', 'n'):
            return False
        raise ValidationError


@implementer(IFromUnicode)
class MessageID(Text):
    """Text string that should be translated.

    When a string is converted to a message ID, it is also
    recorded in the context.
    """

    __factories = {}

    def fromUnicode(self, u):
        context = self.context
        domain = getattr(context, 'i18n_domain', '')
        if not domain:
            domain = 'untranslated'
            warnings.warn(
                "You did not specify an i18n translation domain for the "
                "'%s' field in %s" % (self.getName(), context.info.file)
                )
        v = super(MessageID, self).fromUnicode(u)

        # Check whether there is an explicit message is specified
        default = None
        if v.startswith('[]'):
            v = v[2:].lstrip()
        elif v.startswith('['):
            end = v.find(']')
            default = v[end+2:]
            v = v[1:end]

        # Convert to a message id, importing the factory, if necessary
        factory = self.__factories.get(domain)
        if factory is None:
            import guillotina.i18n
            factory = guillotina.i18n.MessageFactory(domain)
            self.__factories[domain] = factory

        msgid = factory(v, default)

        # Record the string we got for the domain
        i18n_strings = context.i18n_strings
        strings = i18n_strings.get(domain)
        if strings is None:
            strings = i18n_strings[domain] = {}
        locations = strings.setdefault(msgid, [])
        locations.append((context.info.file, context.info.line))

        return msgid

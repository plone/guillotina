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
import sys

PY3 = sys.version_info[0] >= 3

if PY3: #pragma NO COVER

    import builtins
    from io import StringIO

    string_types = str,
    text_type = str
    def b(s):
        return s.encode("latin-1")
    def u(s):
        return s

    # borrowed from 'six'
    print_ = getattr(builtins, "print")

    # borrowed from 'six'
    def reraise(tp, value, tb=None):
        if value is None:
            value = tp
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

else: #pragma NO COVER

    import __builtin__  as builtins
    from StringIO import StringIO

    text_type = unicode
    string_types = basestring,
    def b(s):
        return s
    def u(s):
        return unicode(s, "unicode_escape")

    # borrowed from 'six'
    def print_(*args, **kwargs):
        """The new-style print function."""
        fp = kwargs.pop("file", sys.stdout)
        if fp is None:
            return
        def write(data):
            if not isinstance(data, basestring):
                data = str(data)
            fp.write(data)
        want_unicode = False
        sep = kwargs.pop("sep", None)
        if sep is not None:
            if isinstance(sep, unicode):
                want_unicode = True
            elif not isinstance(sep, str):
                raise TypeError("sep must be None or a string")
        end = kwargs.pop("end", None)
        if end is not None:
            if isinstance(end, unicode):
                want_unicode = True
            elif not isinstance(end, str):
                raise TypeError("end must be None or a string")
        if kwargs:
            raise TypeError("invalid keyword arguments to print()")
        if not want_unicode:
            for arg in args:
                if isinstance(arg, unicode):
                    want_unicode = True
                    break
        if want_unicode:
            newline = unicode("\n")
            space = unicode(" ")
        else:
            newline = "\n"
            space = " "
        if sep is None:
            sep = space
        if end is None:
            end = newline
        for i, arg in enumerate(args):
            if i:
                write(sep)
            write(arg)
        write(end)

    # borrowed from 'six'
    exec("""\
def reraise(tp, value, tb=None):
    raise tp, value, tb
""")

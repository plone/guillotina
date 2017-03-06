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
from types import ModuleType

import os


def resolve(name, package='zopeproducts', _silly=('__doc__',), _globals={}):
    name = name.strip()

    if name.startswith('.'):
        name = package + name

    if name.endswith('.') or name.endswith('+'):
        name = name[:-1]
        repeat = True
    else:
        repeat = False

    names = name.split('.')
    last = names[-1]
    mod = '.'.join(names[:-1])

    if not mod:
        return __import__(name, _globals, _globals, _silly)

    while 1:
        m = __import__(mod, _globals, _globals, _silly)
        try:
            a = getattr(m, last)
        except AttributeError:
            if not repeat:
                return __import__(name, _globals, _globals, _silly)

        else:
            if not repeat or (not isinstance(a, ModuleType)):
                return a
        mod += '.' + last


def getNormalizedName(name, package):
    name = name.strip()
    if name.startswith('.'):
        name = package + name

    if name.endswith('.') or name.endswith('+'):
        name = name[:-1]
        repeat = True
    else:
        repeat = False
    name = name.split(".")
    while len(name) > 1 and name[-1] == name[-2]:
        name.pop()
        repeat = 1
    name = ".".join(name)
    if repeat:
        name += "+"
    return name


def path(file='', package='zopeproducts', _silly=('__doc__',), _globals={}):
    # XXX WTF? why not look for abspath before importing?
    try:
        package = __import__(package, _globals, _globals, _silly)
    except ImportError:
        norm = os.path.normpath(file)
        if file and os.path.abspath(norm) == norm:
            # The package didn't matter
            return norm
        raise

    path = os.path.dirname(package.__file__)

    if file:
        path = os.path.join(path, file)

    return path

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
"""Helper Utility to wrap a text to a set width of characters
"""
__docformat__ = 'restructuredtext'

import re

para_sep = re.compile('\n{2,}')
whitespace = re.compile('[ \t\n\r]+')


def wrap(text, width=78, indent=0):
    """Makes sure that we keep a line length of a certain width.
    """
    paras = para_sep.split(text.strip())

    new_paras = []
    for par in paras:
        words = filter(None, whitespace.split(par))

        lines = []
        line = []
        length = indent
        for word in words:
            if length + len(word) <= width:
                line.append(word)
                length += len(word) + 1
            else:
                lines.append(' '*indent + ' '.join(line))
                line = [word]
                length = len(word) + 1 + indent

        lines.append(' '*indent + ' '.join(line))

        new_paras.append('\n'.join(lines))

    return '\n\n'.join(new_paras) + '\n\n'


def makeDocStructures(context):
    """Creates two structures that provide a friendly format for
    documentation.

    'namespaces' is a dictionary that maps namespaces to a directives
    dictionary with the key being the name of the directive and the value is a
    tuple: (schema, handler, info).

    'subdirs' maps a (namespace, name) pair to a list of subdirectives that
    have the form (namespace, name, schema, info).
    """
    namespaces = {}
    subdirs = {}
    registry = context._docRegistry
    for (namespace, name), schema, usedIn, handler, info, parent in registry:
        if not parent:
            ns_entry = namespaces.setdefault(namespace, {})
            ns_entry[name] = (schema, handler, info)
        else:
            sd_entry = subdirs.setdefault((parent.namespace, parent.name), [])
            sd_entry.append((namespace, name, schema, handler, info))
    return namespaces, subdirs

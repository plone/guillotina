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
""" Utilities for the 'simple directive' section in the narrative docs.
"""

from zope.interface import Interface
from guillotina.schema import Text

from guillotina.configuration.fields import Path
from guillotina.configuration._compat import u

class IRegisterFile(Interface):

    path = Path(
        title=u("File path"),
        description=u("This is the path name of the file to be registered."),
        )

    title = Text(
        title=u("Short summary of the file"),
        description=u("This will be used in file listings"),
        required = False
        )

class FileInfo(object):

    def __init__(self, path, title, description, info):
        (self.path, self.title, self.description, self.info
         ) = path, title, description, info

file_registry = []

def registerFile(context, path, title=u("")):
    info = context.info
    description = info.text.strip()
    context.action(discriminator=('RegisterFile', path),
                   callable=file_registry.append,
                   args=(FileInfo(path, title, description, info),)
                   )

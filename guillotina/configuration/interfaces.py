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
"""Zope Configuration (ZCML) interfaces
"""
from guillotina.configuration._compat import u
from guillotina.schema import BytesLine
from guillotina.schema.interfaces import ValidationError
from zope.interface import Interface


class InvalidToken(ValidationError):
    """Invaid token in list."""


class IConfigurationContext(Interface):
    """Configuration Context

    The configuration context manages information about the state of
    the configuration system, such as the package containing the
    configuration file. More importantly, it provides methods for
    importing objects and opening files relative to the package.
    """

    package = BytesLine(
        title=u("The current package name"),
        description=u("""\
          This is the name of the package containing the configuration
          file being executed. If the configuration file was not
          included by package, then this is None.
          """),
        required=False,
        )

    def resolve(dottedname):
        """Resolve a dotted name to an object

        A dotted name is constructed by concatenating a dotted module
        name with a global name within the module using a dot.  For
        example, the object named "spam" in the foo.bar module has a
        dotted name of foo.bar.spam.  If the current package is a
        prefix of a dotted name, then the package name can be relaced
        with a leading dot, So, for example, if the configuration file
        is in the foo package, then the dotted name foo.bar.spam can
        be shortened to .bar.spam.

        If the current package is multiple levels deep, multiple
        leading dots can be used to refer to higher-level modules.
        For example, if the current package is x.y.z, the dotted
        object name ..foo refers to x.y.foo.
        """

    def path(filename):
        """Compute a full file name for the given file

        If the filename is relative to the package, then the returned
        name will include the package path, otherwise, the original
        file name is returned.
        """

    def checkDuplicate(filename):
        """Check for duplicate imports of the same file.

        Raises an exception if this file had been processed before.  This
        is better than an unlimited number of conflict errors.
        """

    def processFile(filename):
        """Check whether a file needs to be processed.

        Return True if processing is needed and False otherwise.  If
        the file needs to be processed, it will be marked as
        processed, assuming that the caller will procces the file if
        it needs to be procssed.
        """

    def action(discriminator, callable, args=(), kw={}, order=0,
               includepath=None, info=None):
        """Record a configuration action

        The job of most directives is to compute actions for later
        processing.  The action method is used to record those
        actions.  The discriminator is used to to find actions that
        conflict. Actions conflict if they have the same
        discriminator. The exception to this is the special case of
        the discriminator with the value None. An actions with a
        discriminator of None never conflicts with other actions. This
        is possible to add an order argument to crudely control the
        order of execution.  'info' is optional source line information,
        'includepath' is None (the default) or a tuple of include paths for
        this action.
        """

    def provideFeature(name):
        """Record that a named feature is available in this context."""

    def hasFeature(name):
        """Check whether a named feature is available in this context."""


class IGroupingContext(Interface):

    def before():
        """Do something before processing nested directives
        """

    def after():
        """Do something after processing nested directives
        """

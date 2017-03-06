##############################################################################
#
# Copyright (c) 2001, 2002, 2003 Zope Foundation and Contributors.
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
"""Zope configure directive

This file contains the implementation of the Zope configure directive.
It is broken out in a separate file to provide an example of a grouping
directive.

The zope configuration directive is a pure grouping directive.  It
doesn't compute any actions on it's own. Instead, it allows a package
to be specified, affecting the interpretation of relative dotted names
and file paths. It also allows an i18n domain to be specified.  The
information collected is used by subdirectives.

To define a grouping directive, we need to do three things:

- Define a schema for the parameters passed to the directive

- Define a handler class.

- Register the class

The parameter schema is given by IZopeConfigure. It specifies a
package parameter and an i18n_domain parameter.  The package parameter
is specified as a ``GlobalObject``. This means it must be given as a
dotted name that can be resolved through import.  The i18n domain is
just a plain (not unicode) string.

The handler class has a constructor that takes a context to be adapted
and zero or more arguments (depending on the paramter schema).  The
handler class must implement
``guillotina.configuration.interfaces.IGroupingContext``, which defines
hooks ``before`` and ``after``, that are called with no arguments
before and after nested directives are processed.  If a grouping
directive handler creates any actions, or does any computation, this
is normally done in either the ``before`` or ``after`` hooks.
Grouping handlers are normally decorators.

The base class,
``guillotina.configuration.config.GroupingContextDecorator``, is normally
used to define grouping directive handlers. It provides:

- An implementation of IConfigurationContext, which grouping directive
  handlers should normally implement,

- A default implementation of ``IGroupingContext`` that provides empty
  hooks.

- Decorator support that uses a ``__getattr__`` method to delegate
  attribute accesses to adapted contexts, and

- A constructor that sets the ``context`` attribute to the adapted
  context and assigns keyword arguments to attributes.

The ``ZopeConfigure`` provides handling for the ``configure``
directive. It subclasses GroupingContextDecorator, and overrides the
constructor to set the ``basepath`` attribute if a ``package`` argument
is provided. Note that it delegates the job of assigning paramters to
attribute to the ``GroupingContextDecorator`` constructor.

The last step is to register the directive using the meta
configuration directive.  If we wanted to register the Zope
``configure`` directive for the ``zope`` namespace, we'd use a
meta-configuration directive like::

  <meta:groupingDirective
     namespace="http://namespaces.zope.org/zope"
     name="configure"
     schema="guillotina.configuration.zopeconfigure.IZopeConfigure"
     handler="guillotina.configuration.zopeconfigure.ZopeConfigure"
     >
     Zope configure

     The ``configure`` node is normally used as the root node for a
     configuration file.  It can also be used to specify a package or
     internationalization domain for a group of directives within a
     file by grouping those directives.
  </meta:groupingDirective>

We use the groupingDirective meta-directive to register a grouping
directive. The parameters are self explanatory.  The textual contents
of the directive provide documentation text, excluding parameter
documentation, which is provided by the schema.

(The Zope ``configuration`` directive is actually registered using a
lower-level Python API because it is registered for all namespaces,
which isn't supported using the meta-configuration directives.)
"""
__docformat__ = 'restructuredtext'
import os

from zope.interface import Interface
from guillotina.schema import BytesLine

from guillotina.configuration.config import GroupingContextDecorator
from guillotina.configuration.fields import GlobalObject
from guillotina.configuration._compat import u

class IZopeConfigure(Interface):
    """The ``zope:configure`` Directive

    The zope configuration directive is a pure grouping directive.  It
    doesn't compute any actions on it's own. Instead, it allows a package to
    be specified, affecting the interpretation of relative dotted names and
    file paths. It also allows an i18n domain to be specified.  The
    information collected is used by subdirectives.

    It may seem that this directive can only be used once per file, but it can
    be applied whereever it is convenient. 
    """

    package = GlobalObject(
        title=u("Package"),
        description=u("The package to be used for evaluating relative imports "
                      "and file names."),
        required=False)

    i18n_domain = BytesLine(
        title=u("Internationalization domain"),
        description=u("This is a name for the software project. It must be a "
                      "legal file-system name as it will be used to contruct "
                      "names for directories containing translation data. "
                      "\n"
                      "The domain defines a namespace for the message ids "
                      "used by a project."),
        required=False)


class ZopeConfigure(GroupingContextDecorator):
    __doc__ = __doc__

    def __init__(self, context, **kw):
        super(ZopeConfigure, self).__init__(context, **kw)
        if 'package' in kw:
            # if we have a package, we want to also define basepath
            # so we don't acquire one
            self.basepath = os.path.dirname(self.package.__file__)


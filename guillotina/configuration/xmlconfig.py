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
"""Support for the XML configuration file format

Note, for a detailed description of the way that conflicting
configuration actions are resolved, see the detailed example in
test_includeOverrides in tests/test_xmlconfig.py
"""
__docformat__ = 'restructuredtext'

import errno
from glob import glob
import logging
import os
import sys
from xml.sax import make_parser
from xml.sax.xmlreader import InputSource
from xml.sax.handler import ContentHandler, feature_namespaces
from xml.sax import SAXParseException

from zope.interface import Interface
from guillotina.schema import NativeStringLine

from guillotina.configuration.config import ConfigurationMachine
from guillotina.configuration.config import defineGroupingDirective
from guillotina.configuration.config import defineSimpleDirective
from guillotina.configuration.config import GroupingContextDecorator
from guillotina.configuration.config import GroupingStackItem
from guillotina.configuration.config import resolveConflicts
from guillotina.configuration.exceptions import ConfigurationError
from guillotina.configuration.fields import GlobalObject
from guillotina.configuration.zopeconfigure import IZopeConfigure
from guillotina.configuration.zopeconfigure import ZopeConfigure
from guillotina.configuration._compat import StringIO
from guillotina.configuration._compat import reraise
from guillotina.configuration._compat import u

logger = logging.getLogger("config")

ZCML_NAMESPACE = "http://namespaces.zope.org/zcml"
ZCML_CONDITION = (ZCML_NAMESPACE, u("condition"))


class ZopeXMLConfigurationError(ConfigurationError):
    """Zope XML Configuration error

    These errors are wrappers for other errors. They include configuration
    info and the wrapped error type and value.
    """
    def __init__(self, info, etype, evalue):
        self.info, self.etype, self.evalue = info, etype, evalue

    def __str__(self):
        # Only use the repr of the info. This is because we expect to
        # get a parse info and we only want the location information.
        return "%s\n    %s: %s" % (
            repr(self.info), self.etype.__name__, self.evalue)

class ZopeSAXParseException(ConfigurationError):
    """Sax Parser errors, reformatted in an emacs friendly way
    """
    def __init__(self, v):
        self._v = v

    def __str__(self):
        v = self._v
        s = tuple(str(v).split(':'))
        if len(s) == 4:
            return 'File "%s", line %s.%s, %s' % s
        else:
            return str(v)

class ParserInfo(object):
    """Information about a directive based on parser data

    This includes the directive location, as well as text data
    contained in the directive.
    """
    text = u('')

    def __init__(self, file, line, column):
        self.file, self.line, self.column = file, line, column
        self.eline, self.ecolumn = line, column

    def end(self, line, column):
        self.eline, self.ecolumn = line, column

    def __repr__(self):
        if (self.line, self.column) == (self.eline, self.ecolumn):
            return 'File "%s", line %s.%s' % (
                self.file, self.line, self.column)

        return 'File "%s", line %s.%s-%s.%s' % (
            self.file, self.line, self.column, self.eline, self.ecolumn)

    def __str__(self):
        if (self.line, self.column) == (self.eline, self.ecolumn):
            return 'File "%s", line %s.%s' % (
                self.file, self.line, self.column)

        file = self.file
        if file == 'tests//sample.zcml':
            # special case for testing
            file = os.path.join(os.path.dirname(__file__),
                                'tests', 'sample.zcml')

        try:
            with open(file) as f:
                lines = f.readlines()[self.line-1:self.eline]
        except IOError:
            src = "  Could not read source."
        else:
            ecolumn = self.ecolumn
            if lines[-1][ecolumn:ecolumn+2] == '</': #pragma NO COVER
                # We're pointing to the start of an end tag. Try to find
                # the end
                l = lines[-1].find('>', ecolumn)
                if l >= 0:
                    lines[-1] = lines[-1][:l+1]
            else: #pragma NO COVER
                lines[-1] = lines[-1][:ecolumn+1]

            column = self.column
            if lines[0][:column].strip(): #pragma NO COVER
                # Remove text before start if it's noy whitespace
                lines[0] = lines[0][self.column:]

            pad = u('  ')
            blank = u('')
            try:
                src = blank.join([pad + l for l in lines])
            except UnicodeDecodeError: #pragma NO COVER
                # XXX:
                # I hope so most internation zcml will use UTF-8 as encoding
                # otherwise this code must be made more clever
                src = blank.join([pad + l.decode('utf-8') for l in lines])
                # unicode won't be printable, at least on my console
                src = src.encode('ascii','replace')

        return "%s\n%s" % (repr(self), src)

    def characters(self, characters):
        self.text += characters


class ConfigurationHandler(ContentHandler):
    """Interface to the xml parser

    Translate parser events into calls into the configuration system.
    """
    locator = None

    def __init__(self, context, testing=False):
        self.context = context
        self.testing = testing
        self.ignore_depth = 0

    def setDocumentLocator(self, locator):
        self.locator = locator

    def characters(self, text):
        self.context.getInfo().characters(text)

    def startElementNS(self, name, qname, attrs):
        if self.ignore_depth:
            self.ignore_depth += 1
            return

        data = {}
        for (ns, aname), value in attrs.items():
            # NB: even though on CPython, 'ns' will be ``None`` always,
            # do not change the below to "if ns is None" because Jython's
            # sax parser generates attrs that have empty strings for
            # the namepace instead of ``None``.
            if not ns:
                aname = str(aname)
                data[aname] = value
            if (ns, aname) == ZCML_CONDITION:
                # need to process the expression to determine if we
                # use this element and it's descendents
                use = self.evaluateCondition(value)
                if not use:
                    self.ignore_depth = 1
                    return

        info = ParserInfo(
            self.locator.getSystemId(),
            self.locator.getLineNumber(),
            self.locator.getColumnNumber(),
            )

        try:
            self.context.begin(name, data, info)
        except (KeyboardInterrupt, SystemExit): #pragma NO COVER
            raise
        except:
            if self.testing:
                raise
            reraise(ZopeXMLConfigurationError(info,
                                              sys.exc_info()[0],
                                              sys.exc_info()[1]),
                    None, sys.exc_info()[2])

        self.context.setInfo(info)

    def evaluateCondition(self, expression):
        """Evaluate a ZCML condition.

        ``expression`` is a string of the form "verb arguments".

        Currently the supported verbs are ``have``, ``not-have``,
        ``installed`` and ``not-installed``.
        """
        arguments = expression.split(None)
        verb = arguments.pop(0)

        if verb in ('have', 'not-have'):
            if not arguments:
                raise ValueError("Feature name missing: %r" % expression)
            if len(arguments) > 1:
                raise ValueError("Only one feature allowed: %r" % expression)

            if verb == 'have':
                return self.context.hasFeature(arguments[0])
            elif verb == 'not-have':
                return not self.context.hasFeature(arguments[0])

        elif verb in ('installed', 'not-installed'):
            if not arguments:
                raise ValueError("Package name missing: %r" % expression)
            if len(arguments) > 1:
                raise ValueError("Only one package allowed: %r" % expression)

            try:
                __import__(arguments[0])
                installed = True
            except ImportError:
                installed = False

            if verb == 'installed':
                return installed
            elif verb == 'not-installed':
                return not installed
        else:
            raise ValueError("Invalid ZCML condition: %r" % expression)

    def endElementNS(self, name, qname):
        # If ignore_depth is set, this element will be ignored, even
        # if this this decrements ignore_depth to 0.
        if self.ignore_depth:
            self.ignore_depth -= 1
            return

        info = self.context.getInfo()
        info.end(
            self.locator.getLineNumber(),
            self.locator.getColumnNumber(),
            )

        try:
            self.context.end()
        except (KeyboardInterrupt, SystemExit): #pragma NO COVER
            raise
        except:
            if self.testing:
                raise
            reraise(ZopeXMLConfigurationError(info,
                                              sys.exc_info()[0],
                                              sys.exc_info()[1]),
                    None, sys.exc_info()[2])


def processxmlfile(file, context, testing=False):
    """Process a configuration file

    See examples in tests/text_xmlconfig.py
    """
    src = InputSource(getattr(file, 'name', '<string>'))
    src.setByteStream(file)
    parser = make_parser()
    parser.setContentHandler(ConfigurationHandler(context, testing=testing))
    parser.setFeature(feature_namespaces, True)
    try:
        parser.parse(src)
    except SAXParseException:
        reraise(ZopeSAXParseException(sys.exc_info()[1]),
                None, sys.exc_info()[2])


def openInOrPlain(filename):
    """Open a file, falling back to filename.in.

    If the requested file does not exist and filename.in does, fall
    back to filename.in.  If opening the original filename fails for
    any other reason, allow the failure to propogate.
    """
    try:
        return open(filename)
    except IOError as e:
        code, msg = e.args
        if code == errno.ENOENT:
            fn = filename + ".in"
            if os.path.exists(fn):
                return open(fn)
        raise


class IInclude(Interface):
    """The ``include``, ``includeOverrides`` and ``exclude`` directives

    These directives allows you to include or preserve including of another
    ZCML file in the configuration. This enables you to write configuration
    files in each package and then link them together.
    """

    file = NativeStringLine(
        title=u("Configuration file name"),
        description=u("The name of a configuration file to be included/"
                      "excluded, relative to the directive containing the "
                      "including configuration file."),
        required=False,
        )

    files = NativeStringLine(
        title=u("Configuration file name pattern"),
        description=u("""
        The names of multiple configuration files to be included/excluded,
        expressed as a file-name pattern, relative to the directive
        containing the including or excluding configuration file.
        The pattern can include:

        - ``*`` matches 0 or more characters

        - ``?`` matches a single character

        - ``[<seq>]`` matches any character in seq

        - ``[!<seq>]`` matches any character not in seq

        The file names are included in sorted order, where sorting is
        without regard to case.
        """),
        required=False,
        )

    package = GlobalObject(
        title=u("Include or exclude package"),
        description=u("""
        Include or exclude the named file (or configure.zcml) from the
        directory of this package.
        """),
        required=False,
        )


def include(_context, file=None, package=None, files=None):
    """Include a zcml file

    See examples in tests/text_xmlconfig.py
    """

    if files:
        if file:
            raise ValueError("Must specify only one of file or files")
    elif not file:
        file = 'configure.zcml'

    # This is a tad tricky. We want to behave as a grouping directive.

    context = GroupingContextDecorator(_context)
    if package is not None:
        context.package = package
        context.basepath = None

    if files:
        paths = glob(context.path(files))
        paths = sorted(zip([path.lower() for path in paths], paths))
        paths = [path for (l, path) in paths]
    else:
        paths = [context.path(file)]

    for path in paths:
        if context.processFile(path):
            with openInOrPlain(path) as f:
                logger.debug("include %s" % f.name)

                context.basepath = os.path.dirname(path)
                context.includepath = _context.includepath + (f.name, )
                _context.stack.append(GroupingStackItem(context))

                processxmlfile(f, context)
            assert _context.stack[-1].context is context
            _context.stack.pop()

def exclude(_context, file=None, package=None, files=None):
    """Exclude a zcml file
    
    This directive should be used before any ZML that includes
    configuration you want to exclude.
    """

    if files:
        if file:
            raise ValueError("Must specify only one of file or files")
    elif not file:
        file = 'configure.zcml'


    context = GroupingContextDecorator(_context)
    if package is not None:
        context.package = package
        context.basepath = None

    if files:
        paths = glob(context.path(files))
        paths = sorted(zip([path.lower() for path in paths], paths))
        paths = [path for (l, path) in paths]
    else:
        paths = [context.path(file)]

    for path in paths:
        # processFile returns a boolean indicating if the file has been
        # processed or not, it *also* marks the file as having been processed,
        # here the side effect is used to keep the given file from being
        # processed in the future
        context.processFile(path)

def includeOverrides(_context, file=None, package=None, files=None):
    """Include zcml file containing overrides

    The actions in the included file are added to the context as if they
    were in the including file directly.

    See the detailed example in test_includeOverrides in
    tests/text_xmlconfig.py
    """

    # We need to remember how many actions we had before
    nactions = len(_context.actions)

    # We'll give the new actions this include path
    includepath = _context.includepath

    # Now we'll include the file. We'll munge the actions after
    include(_context, file, package, files)

    # Now we'll grab the new actions, resolve conflicts,
    # and munge the includepath:
    newactions = []

    for action in resolveConflicts(_context.actions[nactions:]):
        action['includepath'] = includepath
        newactions.append(action)

    _context.actions[nactions:] = newactions

def registerCommonDirectives(context):
    # We have to use the direct definition functions to define
    # a directive for all namespaces.

    defineSimpleDirective(
        context, "include", IInclude, include, namespace="*")

    defineSimpleDirective(
        context, "exclude", IInclude, exclude, namespace="*")

    defineSimpleDirective(
        context, "includeOverrides", IInclude, includeOverrides, namespace="*")

    defineGroupingDirective(
        context,
        name="configure",
        namespace="*",
        schema=IZopeConfigure,
        handler=ZopeConfigure,
        )

def file(name, package=None, context=None, execute=True):
    """Execute a zcml file
    """

    if context is None:
        context = ConfigurationMachine()
        registerCommonDirectives(context)
        context.package = package

    include(context, name, package)
    if execute:
        context.execute_actions()

    return context

def string(s, context=None, name="<string>", execute=True):
    """Execute a zcml string
    """
    if context is None:
        context = ConfigurationMachine()
        registerCommonDirectives(context)

    f = StringIO(s)
    f.name = name
    processxmlfile(f, context)

    if execute:
        context.execute_actions()

    return context


##############################################################################
# Backward compatability, mainly for tests


_context = None
def _clearContext():
    global _context
    _context = ConfigurationMachine()
    registerCommonDirectives(_context)

def _getContext():
    global _context
    if _context is None:
        _clearContext()
        try:
            from zope.testing.cleanup import addCleanUp
        except ImportError: #pragma NO COVER
            pass
        else: #pragma NO COVER
            addCleanUp(_clearContext)
            del addCleanUp
    return _context

class XMLConfig(object):
    """Provide high-level handling of configuration files.

    See examples in tests/text_xmlconfig.py
    """

    def __init__(self, file_name, module=None):
        context = _getContext()
        include(context, file_name, module)
        self.context = context

    def __call__(self):
        self.context.execute_actions()

def xmlconfig(file, testing=False):
    context = _getContext()
    processxmlfile(file, context, testing=testing)
    context.execute_actions(testing=testing)


def testxmlconfig(file):
    """xmlconfig that doesn't raise configuration errors

    This is useful for testing, as it doesn't mask exception types.
    """
    context = _getContext()
    processxmlfile(file, context, testing=True)
    context.execute_actions(testing=True)


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
"""Configuration processor
"""
from keyword import iskeyword
import operator
import os.path
import sys

from zope.interface.adapter import AdapterRegistry
from zope.interface import Interface
from zope.interface import implementer
from zope.interface import providedBy
from guillotina.schema import TextLine
from guillotina.schema import URI
from guillotina.schema import ValidationError

from guillotina.configuration.exceptions import ConfigurationError
from guillotina.configuration.interfaces import IConfigurationContext
from guillotina.configuration.interfaces import IGroupingContext
from guillotina.configuration.fields import GlobalInterface
from guillotina.configuration.fields import GlobalObject
from guillotina.configuration._compat import builtins
from guillotina.configuration._compat import reraise
from guillotina.configuration._compat import string_types
from guillotina.configuration._compat import text_type
from guillotina.configuration._compat import u


zopens = 'http://namespaces.zope.org/zope'
metans = 'http://namespaces.zope.org/meta'
testns = 'http://namespaces.zope.org/test'

_import_chickens = {}, {}, ("*",)  # dead chickens needed by __import__


class ConfigurationContext(object):
    """Mix-in that implements IConfigurationContext

    Subclasses provide a ``package`` attribute and a ``basepath``
    attribute.  If the base path is not None, relative paths are
    converted to absolute paths using the the base path. If the
    package is not none, relative imports are performed relative to
    the package.

    In general, the basepath and package attributes should be
    consistent. When a package is provided, the base path should be
    set to the path of the package directory.

    Subclasses also provide an ``actions`` attribute, which is a list
    of actions, an ``includepath`` attribute, and an ``info``
    attribute.

    The include path is appended to each action and is used when
    resolving conflicts among actions.  Normally, only the a
    ConfigurationMachine provides the actions attribute. Decorators
    simply use the actions of the context they decorate. The
    ``includepath`` attribute is a tuple of names.  Each name is
    typically the name of an included configuration file.

    The ``info`` attribute contains descriptive information helpful
    when reporting errors.  If not set, it defaults to an empty string.

    The actions attribute is a sequence of dictionaries where each dictionary
    has the following keys:

      - ``discriminator``, a value that identifies the action. Two actions
        that have the same (non None) discriminator conflict.

      - ``callable``, an object that is called to execute the action,

      - ``args``, positional arguments for the action

      - ``kw``, keyword arguments for the action

      - ``includepath``, a tuple of include file names (defaults to ())

      - ``info``, an object that has descriptive information about
        the action (defaults to '')

    """

    def __init__(self):
        super(ConfigurationContext, self).__init__()
        self._seen_files = set()
        self._features = set()

    def resolve(self, dottedname):
        """Resolve a dotted name to an object.
        """
        name = dottedname.strip()

        if not name:
            raise ValueError("The given name is blank")

        if name == '.':
            return self.package

        names = name.split('.')

        if not names[-1]:
            raise ValueError(
                "Trailing dots are no longer supported in dotted names")

        if len(names) == 1:
            # Check for built-in objects
            marker = object()
            obj = getattr(builtins, names[0], marker)
            if obj is not marker:
                return obj

        if not names[0]:
            # Got a relative name. Convert it to abs using package info
            if self.package is None:
                raise ConfigurationError(
                    "Can't use leading dots in dotted names, "
                    "no package has been set.")
            pnames = self.package.__name__.split(".")
            pnames.append('')
            while names and not names[0]:
                names.pop(0)
                try:
                    pnames.pop()
                except IndexError:
                    raise ConfigurationError("Invalid global name", name)
            names[0:0] = pnames

        # Now we should have an absolute dotted name

        # Split off object name:
        oname, mname = names[-1], '.'.join(names[:-1])

        # Import the module
        if not mname:
            # Just got a single name. Must me a module
            mname = oname
            oname = ''

        try:
            mod = __import__(mname, *_import_chickens)
        except ImportError as v:
            if sys.exc_info()[2].tb_next is not None:
                # ImportError was caused deeper
                raise
            raise ConfigurationError(
                "ImportError: Couldn't import %s, %s" % (mname, v))

        if not oname:
            # see not mname case above
            return mod

        try:
            obj = getattr(mod, oname)
            return obj
        except AttributeError:
            # No such name, maybe it's a module that we still need to import
            try:
                return __import__(mname+'.'+oname, *_import_chickens)
            except ImportError:
                if sys.exc_info()[2].tb_next is not None:
                    # ImportError was caused deeper
                    raise
                raise ConfigurationError(
                    "ImportError: Module %s has no global %s" % (mname, oname))

    def path(self, filename):
        """ Compute package-relative paths.
        """
        filename = os.path.normpath(filename)

        if os.path.isabs(filename):
            return filename

        # Got a relative path, combine with base path.
        # If we have no basepath, compute the base path from the package
        # path.
        basepath = getattr(self, 'basepath', '')

        if not basepath:
            if self.package is None:
                basepath = os.getcwd()
            else:
                if hasattr(self.package, '__path__'):
                    basepath = self.package.__path__[0]
                else:
                    basepath = os.path.dirname(self.package.__file__)
                basepath = os.path.abspath(os.path.normpath(basepath))
            self.basepath = basepath

        return os.path.normpath(os.path.join(basepath, filename))

    def checkDuplicate(self, filename):
        """Check for duplicate imports of the same file.

        Raises an exception if this file had been processed before.  This
        is better than an unlimited number of conflict errors.
        """
        path = self.path(filename)
        if path in self._seen_files:
            raise ConfigurationError('%r included more than once' % path)
        self._seen_files.add(path)

    def processFile(self, filename):
        """Check whether a file needs to be processed.

        Return True if processing is needed and False otherwise. If
        the file needs to be processed, it will be marked as
        processed, assuming that the caller will procces the file if
        it needs to be procssed.
        """
        path = self.path(filename)
        if path in self._seen_files:
            return False
        self._seen_files.add(path)
        return True

    def action(self, discriminator, callable=None, args=(), kw=None, order=0,
               includepath=None, info=None, **extra):
        """Add an action with the given discriminator, callable and arguments.

        For testing purposes, the callable and arguments may be omitted.
        In that case, a default noop callable is used.

        The discriminator must be given, but it can be None, to indicate that
        the action never conflicts.
        """
        if kw is None:
            kw = {}

        action = extra

        if info is None:
            info = getattr(self, 'info', '')

        if includepath is None:
            includepath = getattr(self, 'includepath', ())

        action.update(
            dict(
                discriminator=discriminator,
                callable=callable,
                args=args,
                kw=kw,
                includepath=includepath,
                info=info,
                order=order,
                )
            )

        self.actions.append(action)

    def hasFeature(self, feature):
        """Check whether a named feature has been provided.

        Initially no features are provided
        """
        return feature in self._features

    def provideFeature(self, feature):
        """Declare thata named feature has been provided.

        See :meth:`hasFeature` for examples.
        """
        self._features.add(feature)


class ConfigurationAdapterRegistry(object):
    """Simple adapter registry that manages directives as adapters
    """

    def __init__(self):
        super(ConfigurationAdapterRegistry, self).__init__()
        self._registry = {}
        # Stores tuples of form:
        #   (namespace, name), schema, usedIn, info, parent
        self._docRegistry = []

    def register(self, interface, name, factory):
        r = self._registry.get(name)
        if r is None:
            r = AdapterRegistry()
            self._registry[name] = r

        r.register([interface], Interface, '', factory)

    def document(self, name, schema, usedIn, handler, info, parent=None):
        if isinstance(name, string_types):
            name = ('', name)
        self._docRegistry.append((name, schema, usedIn, handler, info, parent))

    def factory(self, context, name):
        r = self._registry.get(name)
        if r is None:
            # Try namespace-independent name
            ns, n = name
            r = self._registry.get(n)
            if r is None:
                raise ConfigurationError("Unknown directive", ns, n)

        f = r.lookup1(providedBy(context), Interface)
        if f is None:
            raise ConfigurationError(
                "The directive %s cannot be used in this context" % (name, ))
        return f


@implementer(IConfigurationContext)
class ConfigurationMachine(ConfigurationAdapterRegistry, ConfigurationContext):
    """Configuration machine
    """
    package = None
    basepath = None
    includepath = ()
    info = ''

    def __init__(self):
        super(ConfigurationMachine, self).__init__()
        self.actions = []
        self.stack = [RootStackItem(self)]
        self.i18n_strings = {}
        _bootstrap(self)

    def begin(self, __name, __data=None, __info=None, **kw):
        if __data:
            if kw:
                raise TypeError("Can't provide a mapping object and keyword "
                                "arguments")
        else:
            __data = kw
        self.stack.append(self.stack[-1].contained(__name, __data, __info))

    def end(self):
        self.stack.pop().finish()

    def __call__(self, __name, __info=None, **__kw):
        self.begin(__name, __kw, __info)
        self.end()

    def getInfo(self):
        return self.stack[-1].context.info

    def setInfo(self, info):
        self.stack[-1].context.info = info

    def execute_actions(self, clear=True, testing=False):
        """Execute the configuration actions.

        This calls the action callables after resolving conflicts.
        """
        try:
            for action in resolveConflicts(self.actions):
                callable = action['callable']
                if callable is None:
                    continue
                args = action['args']
                kw = action['kw']
                info = action['info']
                try:
                    callable(*args, **kw)
                except (KeyboardInterrupt, SystemExit):  # pragma NO COVER
                    raise
                except:
                    if testing:
                        raise
                    t, v, tb = sys.exc_info()
                    try:
                        reraise(ConfigurationExecutionError(t, v, info),
                                None, tb)
                    finally:
                        del t, v, tb

        finally:
            if clear:
                del self.actions[:]


class ConfigurationExecutionError(ConfigurationError):
    """An error occurred during execution of a configuration action
    """
    def __init__(self, etype, evalue, info):
        self.etype, self.evalue, self.info = etype, evalue, info

    def __str__(self):  # pragma NO COVER
        return "%s: %s\n  in:\n  %s" % (self.etype, self.evalue, self.info)

##############################################################################
# Stack items


class IStackItem(Interface):
    """Configuration machine stack items

    Stack items are created when a directive is being processed.

    A stack item is created for each directive use.
    """

    def contained(name, data, info):
        """Begin processing a contained directive

        The data are a dictionary of attribute names mapped to unicode
        strings.

        The info argument is an object that can be converted to a
        string and that contains information about the directive.

        The begin method returns the next item to be placed on the stack.
        """

    def finish():
        """Finish processing a directive
        """


@implementer(IStackItem)
class SimpleStackItem(object):
    """Simple stack item

    A simple stack item can't have anything added after it.  It can
    only be removed.  It is used for simple directives and
    subdirectives, which can't contain other directives.

    It also defers any computation until the end of the directive
    has been reached.
    """
    # XXX why this *argdata hack instead of schema, data?
    def __init__(self, context, handler, info, *argdata):
        newcontext = GroupingContextDecorator(context)
        newcontext.info = info
        self.context = newcontext
        self.handler = handler
        self.argdata = argdata

    def contained(self, name, data, info):
        raise ConfigurationError("Invalid directive %s" % str(name))

    def finish(self):
        # We're going to use the context that was passed to us, which wasn't
        # created for the directive.  We want to set it's info to the one
        # passed to us while we make the call, so we'll save the old one
        # and restore it.
        context = self.context
        args = toargs(context, *self.argdata)
        actions = self.handler(context, **args)
        if actions:
            # we allow the handler to return nothing
            for action in actions:
                if not isinstance(action, dict):
                    action = expand_action(*action)  # b/c
                context.action(**action)


@implementer(IStackItem)
class RootStackItem(object):

    def __init__(self, context):
        self.context = context

    def contained(self, name, data, info):
        """Handle a contained directive

        We have to compute a new stack item by getting a named adapter
        for the current context object.
        """
        factory = self.context.factory(self.context, name)
        if factory is None:
            raise ConfigurationError("Invalid directive", name)
        adapter = factory(self.context, data, info)
        return adapter

    def finish(self):
        pass


@implementer(IStackItem)
class GroupingStackItem(RootStackItem):
    """Stack item for a grouping directive

    A grouping stack item is in the stack when a grouping directive is
    being processed.  Grouping directives group other directives.
    Often, they just manage common data, but they may also take
    actions, either before or after contained directives are executed.

    A grouping stack item is created with a grouping directive
    definition, a configuration context, and directive data.
    """

    def __init__(self, context):
        super(GroupingStackItem, self).__init__(context)

    def __callBefore(self):
        actions = self.context.before()
        if actions:
            for action in actions:
                if not isinstance(action, dict):
                    action = expand_action(*action)
                self.context.action(**action)
        self.__callBefore = noop

    def contained(self, name, data, info):
        self.__callBefore()
        return RootStackItem.contained(self, name, data, info)

    def finish(self):
        self.__callBefore()
        actions = self.context.after()
        if actions:
            for action in actions:
                if not isinstance(action, dict):
                    action = expand_action(*action)
                self.context.action(**action)


def noop():
    pass


@implementer(IStackItem)
class ComplexStackItem(object):
    """Complex stack item

    A complex stack item is in the stack when a complex directive is
    being processed.  It only allows subdirectives to be used.

    A complex stack item is created with a complex directive
    definition (IComplexDirectiveContext), a configuration context,
    and directive data.
    """
    def __init__(self, meta, context, data, info):
        newcontext = GroupingContextDecorator(context)
        newcontext.info = info
        self.context = newcontext
        self.meta = meta

        # Call the handler contructor
        args = toargs(newcontext, meta.schema, data)
        self.handler = self.meta.handler(newcontext, **args)

    def contained(self, name, data, info):
        """Handle a subdirective
        """
        # Look up the subdirective meta data on our meta object
        ns, name = name
        schema = self.meta.get(name)
        if schema is None:
            raise ConfigurationError("Invalid directive", name)
        schema = schema[0]  # strip off info
        handler = getattr(self.handler, name)
        return SimpleStackItem(self.context, handler, info, schema, data)

    def finish(self):
        # when we're done, we call the handler, which might return more actions
        # Need to save and restore old info
        # XXX why not just use callable()?
        try:
            actions = self.handler()
        except AttributeError as v:
            if v.args[0] == '__call__':
                return  # noncallable
            raise
        except TypeError:
            return  # non callable

        if actions:
            # we allow the handler to return nothing
            for action in actions:
                if not isinstance(action, dict):
                    action = expand_action(*action)
                self.context.action(**action)


##############################################################################
# Helper classes

@implementer(IConfigurationContext, IGroupingContext)
class GroupingContextDecorator(ConfigurationContext):
    """Helper mix-in class for building grouping directives

    See the discussion (and test) in GroupingStackItem.
    """

    def __init__(self, context, **kw):
        self.context = context
        for name, v in kw.items():
            setattr(self, name, v)

    def __getattr__(self, name,
                    getattr=getattr, setattr=setattr):
        v = getattr(self.context, name)
        # cache result in self
        setattr(self, name, v)
        return v

    def before(self):
        pass

    def after(self):
        pass

##############################################################################
# Directive-definition


class DirectiveSchema(GlobalInterface):
    """A field that contains a global variable value that must be a schema
    """


class IDirectivesInfo(Interface):
    """Schema for the ``directives`` directive
    """

    namespace = URI(
        title=u("Namespace"),
        description=u("The namespace in which directives' names "
                      "will be defined"),
        )


class IDirectivesContext(IDirectivesInfo, IConfigurationContext):
    pass


@implementer(IDirectivesContext)
class DirectivesHandler(GroupingContextDecorator):
    """Handler for the directives directive

    This is just a grouping directive that adds a namespace attribute
    to the normal directive context.

    """


class IDirectiveInfo(Interface):
    """Information common to all directive definitions have
    """

    name = TextLine(
        title=u("Directive name"),
        description=u("The name of the directive being defined"),
        )

    schema = DirectiveSchema(
        title=u("Directive handler"),
        description=u("The dotted name of the directive handler"),
        )


class IFullInfo(IDirectiveInfo):
    """Information that all top-level directives (not subdirectives) have
    """

    handler = GlobalObject(
        title=u("Directive handler"),
        description=u("The dotted name of the directive handler"),
        )

    usedIn = GlobalInterface(
        title=u("The directive types the directive can be used in"),
        description=u("The interface of the directives that can contain "
                      "the directive"),
        default=IConfigurationContext,
        )


class IStandaloneDirectiveInfo(IDirectivesInfo, IFullInfo):
    """Info for full directives defined outside a directives directives
    """


def defineSimpleDirective(context, name, schema, handler,
                          namespace='', usedIn=IConfigurationContext):
    """Define a simple directive

    Define and register a factory that invokes the simple directive
    and returns a new stack item, which is always the same simple stack item.

    If the namespace is '*', the directive is registered for all namespaces.
    """
    namespace = namespace or context.namespace
    if namespace != '*':
        name = namespace, name

    def factory(context, data, info):
        return SimpleStackItem(context, handler, info, schema, data)
    factory.schema = schema

    context.register(usedIn, name, factory)
    context.document(name, schema, usedIn, handler, context.info)


def defineGroupingDirective(context, name, schema, handler,
                            namespace='', usedIn=IConfigurationContext):
    """Define a grouping directive

    Define and register a factory that sets up a grouping directive.

    If the namespace is '*', the directive is registered for all namespaces.
    """
    namespace = namespace or context.namespace
    if namespace != '*':
        name = namespace, name

    def factory(context, data, info):
        args = toargs(context, schema, data)
        newcontext = handler(context, **args)
        newcontext.info = info
        return GroupingStackItem(newcontext)
    factory.schema = schema

    context.register(usedIn, name, factory)
    context.document(name, schema, usedIn, handler, context.info)


class IComplexDirectiveContext(IFullInfo, IConfigurationContext):
    pass


@implementer(IComplexDirectiveContext)
class ComplexDirectiveDefinition(GroupingContextDecorator, dict):
    """Handler for defining complex directives

    See the description and tests for ComplexStackItem.
    """
    def before(self):

        def factory(context, data, info):
            return ComplexStackItem(self, context, data, info)
        factory.schema = self.schema

        self.register(self.usedIn, (self.namespace, self.name), factory)
        self.document((self.namespace, self.name), self.schema, self.usedIn,
                      self.handler, self.info)


def subdirective(context, name, schema):
    context.document((context.namespace, name), schema, context.usedIn,
                     getattr(context.handler, name, context.handler),
                     context.info, context.context)
    context.context[name] = schema, context.info

##############################################################################
# Features


class IProvidesDirectiveInfo(Interface):
    """Information for a <meta:provides> directive"""

    feature = TextLine(
        title=u("Feature name"),
        description=u("""The name of the feature being provided

        You can test available features with zcml:condition="have featurename".
        """),
        )


def provides(context, feature):
    """Declare that a feature is provided in context.
    """
    if len(feature.split()) > 1:
        raise ValueError("Only one feature name allowed")
    context.provideFeature(feature)


##############################################################################
# Argument conversion

def toargs(context, schema, data):
    """Marshal data to an argument dictionary using a schema

    Names that are python keywords have an underscore added as a
    suffix in the schema and in the argument list, but are used
    without the underscore in the data.

    The fields in the schema must all implement IFromUnicode.

    All of the items in the data must have corresponding fields in the
    schema unless the schema has a true tagged value named
    'keyword_arguments'.
    """
    data = dict(data)
    args = {}
    for name, field in schema.namesAndDescriptions(True):
        field = field.bind(context)
        n = name
        if n.endswith('_') and iskeyword(n[:-1]):
            n = n[:-1]

        s = data.get(n, data)
        if s is not data:
            s = text_type(s)
            del data[n]

            try:
                args[str(name)] = field.fromUnicode(s)
            except ValidationError as v:
                reraise(ConfigurationError("Invalid value for", n, str(v)),
                        None, sys.exc_info()[2])
        elif field.required:
            # if the default is valid, we can use that:
            default = field.default
            try:
                field.validate(default)
            except ValidationError:
                raise ConfigurationError("Missing parameter:", n)
            args[str(name)] = default

    if data:
        # we had data left over
        try:
            keyword_arguments = schema.getTaggedValue('keyword_arguments')
        except KeyError:
            keyword_arguments = False
        if not keyword_arguments:
            raise ConfigurationError("Unrecognized parameters:", *data)

        for name in data:
            args[str(name)] = data[name]

    return args

##############################################################################
# Conflict resolution


def expand_action(discriminator, callable=None, args=(), kw=None,
                  includepath=(), info=None, order=0, **extra):
    if kw is None:
        kw = {}
    action = extra
    action.update(
        dict(
            discriminator=discriminator,
            callable=callable,
            args=args,
            kw=kw,
            includepath=includepath,
            info=info,
            order=order,
            )
        )
    return action


def resolveConflicts(actions):
    """Resolve conflicting actions

    Given an actions list, identify and try to resolve conflicting actions.
    Actions conflict if they have the same non-None discriminator.
    Conflicting actions can be resolved if the include path of one of
    the actions is a prefix of the includepaths of the other
    conflicting actions and is unequal to the include paths in the
    other conflicting actions.
    """

    # organize actions by discriminators
    unique = {}
    output = []
    for i, action in enumerate(actions):
        if not isinstance(action, dict):
            # old-style tuple action
            action = expand_action(*action)

        # "order" is an integer grouping. Actions in a lower order will be
        # executed before actions in a higher order.  Within an order,
        # actions are executed sequentially based on original action ordering
        # ("i").
        order = action['order'] or 0
        discriminator = action['discriminator']

        # "ainfo" is a tuple of (order, i, action) where "order" is a
        # user-supplied grouping, "i" is an integer expressing the relative
        # position of this action in the action list being resolved, and
        # "action" is an action dictionary.  The purpose of an ainfo is to
        # associate an "order" and an "i" with a particular action; "order"
        # and "i" exist for sorting purposes after conflict resolution.
        ainfo = (order, i, action)

        if discriminator is None:
            # The discriminator is None, so this action can never conflict.
            # We can add it directly to the result.
            output.append(ainfo)
            continue

        L = unique.setdefault(discriminator, [])
        L.append(ainfo)

    # Check for conflicts
    conflicts = {}

    for discriminator, ainfos in unique.items():

        # We use (includepath, order, i) as a sort key because we need to
        # sort the actions by the paths so that the shortest path with a
        # given prefix comes first.  The "first" action is the one with the
        # shortest include path.  We break sorting ties using "order", then
        # "i".
        def bypath(ainfo):
            path, order, i = ainfo[2]['includepath'], ainfo[0], ainfo[1]
            return path, order, i

        ainfos.sort(key=bypath)
        ainfo, rest = ainfos[0], ainfos[1:]
        output.append(ainfo)
        _, _, action = ainfo
        basepath, baseinfo, discriminator = (action['includepath'],
                                             action['info'],
                                             action['discriminator'])

        for _, _, action in rest:
            includepath = action['includepath']
            # Test whether path is a prefix of opath
            if (includepath[:len(basepath)] != basepath or includepath == basepath):
                L = conflicts.setdefault(discriminator, [baseinfo])
                L.append(action['info'])

    if conflicts:
        raise ConfigurationConflictError(conflicts)

    # Sort conflict-resolved actions by (order, i) and return them.
    return [x[2] for x in sorted(output, key=operator.itemgetter(0, 1))]


class ConfigurationConflictError(ConfigurationError):

    def __init__(self, conflicts):
        self._conflicts = conflicts

    def __str__(self):  # pragma NO COVER
        r = ["Conflicting configuration actions"]
        items = self._conflicts.items()
        items.sort()
        for discriminator, infos in items:
            r.append("  For: %s" % (discriminator, ))
            for info in infos:
                for line in text_type(info).rstrip().split(u('\n')):
                    r.append(u("    ") + line)

        return "\n".join(r)


##############################################################################
# Bootstap code


def _bootstrap(context):

    # Set enough machinery to register other directives

    # Define the directive (simple directive) directive by calling it's
    # handler directly

    info = 'Manually registered in zope/configuration/config.py'

    context.info = info
    defineSimpleDirective(
        context,
        namespace=metans, name='directive',
        schema=IStandaloneDirectiveInfo,
        handler=defineSimpleDirective)
    context.info = ''

    # OK, now that we have that, we can use the machine to define the
    # other directives. This isn't the easiest way to proceed, but it lets
    # us eat our own dogfood. :)

    # Standalone groupingDirective
    context((metans, 'directive'),
            info,
            name='groupingDirective',
            namespace=metans,
            handler="guillotina.configuration.config.defineGroupingDirective",
            schema="guillotina.configuration.config.IStandaloneDirectiveInfo"
            )

    # Now we can use the grouping directive to define the directives directive
    context((metans, 'groupingDirective'),
            info,
            name='directives',
            namespace=metans,
            handler="guillotina.configuration.config.DirectivesHandler",
            schema="guillotina.configuration.config.IDirectivesInfo"
            )

    # directive and groupingDirective inside directives
    context((metans, 'directive'),
            info,
            name='directive',
            namespace=metans,
            usedIn="guillotina.configuration.config.IDirectivesContext",
            handler="guillotina.configuration.config.defineSimpleDirective",
            schema="guillotina.configuration.config.IFullInfo"
            )
    context((metans, 'directive'),
            info,
            name='groupingDirective',
            namespace=metans,
            usedIn="guillotina.configuration.config.IDirectivesContext",
            handler="guillotina.configuration.config.defineGroupingDirective",
            schema="guillotina.configuration.config.IFullInfo"
            )

    # Setup complex directive directive, both standalone, and in
    # directives directive
    context((metans, 'groupingDirective'),
            info,
            name='complexDirective',
            namespace=metans,
            handler="guillotina.configuration.config.ComplexDirectiveDefinition",
            schema="guillotina.configuration.config.IStandaloneDirectiveInfo"
            )
    context((metans, 'groupingDirective'),
            info,
            name='complexDirective',
            namespace=metans,
            usedIn="guillotina.configuration.config.IDirectivesContext",
            handler="guillotina.configuration.config.ComplexDirectiveDefinition",
            schema="guillotina.configuration.config.IFullInfo"
            )

    # Finally, setup subdirective directive
    context((metans, 'directive'),
            info,
            name='subdirective',
            namespace=metans,
            usedIn="guillotina.configuration.config.IComplexDirectiveContext",
            handler="guillotina.configuration.config.subdirective",
            schema="guillotina.configuration.config.IDirectiveInfo"
            )

    # meta:provides
    context((metans, 'directive'),
            info,
            name='provides',
            namespace=metans,
            handler="guillotina.configuration.config.provides",
            schema="guillotina.configuration.config.IProvidesDirectiveInfo"
            )

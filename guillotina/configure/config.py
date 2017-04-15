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
from guillotina.exceptions import ConfigurationError
from guillotina.interfaces.configuration import IConfigurationContext
from guillotina.interfaces.configuration import IGroupingContext
from guillotina.schema import ValidationError
from keyword import iskeyword
from zope.interface import implementer
from zope.interface import Interface

import operator
import sys


def reraise(tp, value, tb=None):
    if value is None:
        value = tp
    if value.__traceback__ is not tb:
        raise value.with_traceback(tb)
    raise value


_import_chickens = {}, {}, ("*",)  # dead chickens needed by __import__


class ConfigurationContext(object):
    """Mix-in that implements IConfigurationContext

    The actions attribute is a sequence of dictionaries where each dictionary
    has the following keys:

      - ``discriminator``, a value that identifies the action. Two actions
        that have the same (non None) discriminator conflict.

      - ``callable``, an object that is called to execute the action,

      - ``args``, positional arguments for the action

      - ``kw``, keyword arguments for the action

    """

    def __init__(self):
        super(ConfigurationContext, self).__init__()
        # on commit, we increment so we can override registered components
        self.count = 0
        self.module_name = 'guillotina'

    def begin(self, module_name):
        self.module_name = module_name

    def commit(self):
        self.count += 1

    def action(self, discriminator, callable=None, args=(), kw=None, **extra):
        """Add an action with the given discriminator, callable and arguments.

        For testing purposes, the callable and arguments may be omitted.
        In that case, a default noop callable is used.

        The discriminator must be given, but it can be None, to indicate that
        the action never conflicts.
        """
        if kw is None:
            kw = {}

        action = extra

        action.update(dict(
            discriminator=discriminator,
            callable=callable,
            args=args,
            kw=kw,
            module_name=self.module_name,
            order=self.count))

        self.actions.append(action)


@implementer(IConfigurationContext)
class ConfigurationMachine(ConfigurationContext):
    """Configuration machine
    """

    def __init__(self):
        super(ConfigurationMachine, self).__init__()
        self.actions = []
        self.stack = [RootStackItem(self)]

    def execute_actions(self, clear=True, testing=False):
        """Execute the configuration actions.

        This calls the action callables after resolving conflicts.
        """
        try:
            for action in resolve_conflicts(self.actions):
                callable = action['callable']
                if callable is None:
                    continue
                args = action['args']
                kw = action['kw']
                try:
                    callable(*args, **kw)
                except (KeyboardInterrupt, SystemExit):  # pragma NO COVER
                    raise
                except:  # noqa
                    if testing:
                        raise
                    t, v, tb = sys.exc_info()
                    try:
                        reraise(ConfigurationExecutionError(t, v),
                                None, tb)
                    finally:
                        del t, v, tb

        finally:
            if clear:
                del self.actions[:]


class ConfigurationExecutionError(ConfigurationError):
    """An error occurred during execution of a configuration action
    """
    def __init__(self, etype, evalue):
        self.etype, self.evalue = etype, evalue

    def __str__(self):  # pragma NO COVER
        return "%s: %s\n  in:\n  %s" % (self.etype, self.evalue)


##############################################################################
# Stack items

class IStackItem(Interface):
    """Configuration machine stack items

    Stack items are created when a directive is being processed.

    A stack item is created for each directive use.
    """

    def contained(name, data):
        """Begin processing a contained directive

        The data are a dictionary of attribute names mapped to unicode
        strings.

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
    def __init__(self, context, handler, *argdata):
        newcontext = GroupingContextDecorator(context)
        self.context = newcontext
        self.handler = handler
        self.argdata = argdata

    def contained(self, name, data):
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

    def contained(self, name, data):
        """Handle a contained directive

        We have to compute a new stack item by getting a named adapter
        for the current context object.
        """
        factory = self.context.factory(self.context, name)
        if factory is None:
            raise ConfigurationError("Invalid directive", name)
        adapter = factory(self.context, data)
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

    def __call_before(self):
        actions = self.context.before()
        if actions:
            for action in actions:
                if not isinstance(action, dict):
                    action = expand_action(*action)
                self.context.action(**action)
        self.__call_before = noop

    def contained(self, name, data):
        self.__call_before()
        return RootStackItem.contained(self, name, data)

    def finish(self):
        self.__call_before()
        actions = self.context.after()
        if actions:
            for action in actions:
                if not isinstance(action, dict):
                    action = expand_action(*action)
                self.context.action(**action)


def noop():
    pass


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
            s = str(s)
            del data[n]

            try:
                args[str(name)] = field.from_unicode(s)
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
                  order=0, **extra):
    if kw is None:
        kw = {}
    action = extra
    action.update(
        dict(
            discriminator=discriminator,
            callable=callable,
            args=args,
            kw=kw,
            order=order))
    return action


def resolve_conflicts(actions):
    """Resolve conflicting actions

    Given an actions list, identify and try to resolve conflicting actions.
    Actions conflict if they have the same non-None discriminator.
    Conflicting actions can be resolved by the order they were included
    by configured application
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

        L = unique.setdefault(discriminator, [])  # noqa
        L.append(ainfo)

    # Check for conflicts
    conflicts = {}

    for discriminator, ainfos in unique.items():

        # We use (order, i) as a sort key because we need to
        def byorder(ainfo):
            order, i = ainfo[0], ainfo[1]
            return order, i

        ainfos.sort(key=byorder)
        ainfo, rest = ainfos[0], ainfos[1:]
        output.append(ainfo)
        _, _, action = ainfo
        order = action['order']
        discriminator = action['discriminator']
        base_module_name = action['module_name']
        base_order = action['order']

        for _, _, action in rest:
            if action['order'] <= base_order:
                L = conflicts.setdefault(discriminator, [base_module_name, base_order])  # noqa
                L.append((action['module_name'], action['order']))

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
                for line in str(info).rstrip().split('\n'):
                    r.append("    " + line)

        return "\n".join(r)

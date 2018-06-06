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
from zope.interface import implementer

import operator
import sys


def reraise(tp, value, tb=None):
    if value is None:
        value = tp
    if value.__traceback__ is not tb:
        raise value.with_traceback(tb)
    raise value


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
        return '%s: %s\n  in:\n  %s' % (self.etype, self.evalue)


##############################################################################
# Conflict resolution


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
        r = ['Conflicting configuration actions']
        items = [(k, v) for k, v in self._conflicts.items()]
        items.sort()
        for discriminator, infos in items:
            r.append('  For: %s' % (discriminator, ))
            for info in infos:
                for line in str(info).rstrip().split('\n'):
                    r.append('    ' + line)

        return '\n'.join(r)

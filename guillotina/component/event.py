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
# flake8: noqa
from guillotina.component._api import subscribers as component_subscribers
from guillotina.component._api import get_component_registry
from guillotina.component.interfaces import ComponentLookupError


async_subscribers = []
sync_subscribers = []


def dispatch(*event):
    component_subscribers(event, None)


async def async_dispatch(*event):
    try:
        sitemanager = get_component_registry()
    except ComponentLookupError:
        # Oh blast, no site manager. This should *never* happen!
        return []

    return await sitemanager.adapters.asubscribers(event, None)


async_subscribers.append(async_dispatch)
sync_subscribers.append(dispatch)

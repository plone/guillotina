##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
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
from guillotina.component._compat import _BLANK
from guillotina.component.interfaces import IComponentLookup
from guillotina.profile import profilable
from zope.interface import implementer
from zope.interface import providedBy
from zope.interface.adapter import AdapterLookup
from zope.interface.adapter import AdapterRegistry
from zope.interface.registry import Components

import asyncio
import logging
import os
import time


profile_logger = logging.getLogger("guillotina.profile")


class GuillotinaAdapterLookup(AdapterLookup):
    @profilable
    async def asubscribers(self, objects, provided):
        subscriptions = self.subscriptions(map(providedBy, objects), provided)
        results = []
        for subscription in sorted(subscriptions, key=lambda sub: getattr(sub, "priority", 100)):
            if asyncio.iscoroutinefunction(subscription):
                results.append(await subscription(*objects))
            else:
                results.append(subscription(*objects))
        return results

    @profilable
    def subscribers(self, objects, provided):
        subscriptions = self.subscriptions(map(providedBy, objects), provided)
        result = []
        for subscription in sorted(subscriptions, key=lambda sub: getattr(sub, "priority", 100)):
            if not asyncio.iscoroutinefunction(subscription):
                result.append(subscription(*objects))
        return result


class DebugGuillotinaAdapterLookup(GuillotinaAdapterLookup):  # pragma: no cover
    @profilable
    async def asubscribers(self, objects, provided):
        from guillotina.utils import get_current_request, get_authenticated_user_id, get_dotted_name
        from guillotina.exceptions import RequestNotFound
        from guillotina import task_vars

        try:
            request = get_current_request()
        except RequestNotFound:
            request = None
        try:
            url = request.url.human_repr()
        except AttributeError:
            # older version of aiohttp
            url = ""
        info = {
            "url": url,
            "account": getattr(task_vars.container.get(), "id", None),
            "user": get_authenticated_user_id(),
            "db_id": getattr(task_vars.db.get(), "id", None),
            "request_uid": getattr(request, "_uid", None),
            "method": getattr(request, "method", None),
            "subscribers": [],
            "provided": repr(provided),
            "objects": repr(objects),
            "start": time.time() * 1000,
        }
        subscriptions = sorted(
            self.subscriptions(map(providedBy, objects), provided),
            key=lambda sub: getattr(sub, "priority", 100),
        )
        info["lookup_time"] = (time.time() * 1000) - info["start"]
        info["found"] = len(subscriptions)
        results = []
        for subscription in subscriptions:
            start = time.time() * 1000
            if asyncio.iscoroutinefunction(subscription):
                results.append(await subscription(*objects))
            else:
                results.append(subscription(*objects))
            info["subscribers"].append(
                {"duration": (time.time() * 1000) - start, "name": get_dotted_name(subscription)}
            )
        info["end"] = (time.time() * 1000) - info["start"]
        profile_logger.info(info)
        return results


class GuillotinaAdapterRegistry(AdapterRegistry):
    """
    Customized adapter registry for async
    """

    _delegated = AdapterRegistry._delegated + ("asubscribers",)  # type: ignore
    if os.environ.get("DEBUG_SUBSCRIBERS") in ("1", "true", "t") or True:
        LookupClass = DebugGuillotinaAdapterLookup
    else:
        LookupClass = GuillotinaAdapterLookup

    def __init__(self, parent, name):
        self.__parent__ = parent
        self.__name__ = name
        super().__init__()


@implementer(IComponentLookup)
class GlobalComponents(Components):
    def _init_registries(self):
        self.adapters = GuillotinaAdapterRegistry(self, "adapters")
        self.utilities = GuillotinaAdapterRegistry(self, "utilities")

    def __reduce__(self):
        # Global site managers are pickled as global objects
        return self.__name__


base = GlobalComponents("base")


def get_global_components():
    return base


def reset():
    global base
    base = GlobalComponents("base")


def provide_utility(component, provides=None, name=_BLANK):
    base.registerUtility(component, provides, name, event=False)


def provide_adapter(factory, adapts=None, provides=None, name=_BLANK):
    base.registerAdapter(factory, adapts, provides, name, event=False)


def provide_subscription_adapter(factory, adapts=None, provides=None):
    base.registerSubscriptionAdapter(factory, adapts, provides, event=False)


def provide_handler(factory, adapts=None):
    base.registerHandler(factory, adapts, event=False)

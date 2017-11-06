from guillotina.profile import profilable
from zope.interface import providedBy
from zope.interface.adapter import AdapterLookupBase
from zope.interface.adapter import BaseAdapterRegistry

import asyncio


BaseAdapterRegistry._delegated = (
    'lookup', 'queryMultiAdapter', 'lookup1', 'queryAdapter',
    'adapter_hook', 'lookupAll', 'names',
    'subscriptions', 'subscribers', 'asubscribers')


@profilable
async def asubscribers(self, objects, provided):
    subscriptions = self.subscriptions(map(providedBy, objects), provided)
    results = []
    for subscription in subscriptions:
        if asyncio.iscoroutinefunction(subscription):
            results.append(await subscription(*objects))
    return results


@profilable
def subscribers(self, objects, provided):
    subscriptions = self.subscriptions(map(providedBy, objects), provided)
    result = []
    for subscription in subscriptions:
        if not asyncio.iscoroutinefunction(subscription):
            result.append(subscription(*objects))
    return result


AdapterLookupBase.asubscribers = asubscribers
AdapterLookupBase.subscribers = subscribers

from guillotina.catalog.catalog import DefaultSecurityInfoAdapter
from guillotina.component import get_multi_adapter
from guillotina.component import getAdapter
from guillotina.interfaces import IResourceDeserializeFromJson
from guillotina.interfaces import ISecurityInfo
from guillotina.tests import utils as test_utils

import time


ITERATIONS = 1000000


# ----------------------------------------------------
# Measure performance of different types of lookups
#
# Lessons:
#   - Adapters with only 1 lookup aren't much slower than doing your own manual lookup
#   - Each additional thing you're adapting makes your lookup about 1/3
#     more slow(depending on the interface stack)
#   - Keep adapter simple, using callable with params is usually faster and more simple
# ----------------------------------------------------


async def run1():
    ob = test_utils.create_content()
    print('Test single adapter lookup')
    start = time.time()
    for _ in range(ITERATIONS):
        getAdapter(ob, ISecurityInfo)
    end = time.time()
    print(f'Done with {ITERATIONS} in {end - start} seconds')


async def run2():
    ob = test_utils.create_content()
    req = test_utils.get_mocked_request()
    start = time.time()
    print('Test multi adapter')
    for _ in range(ITERATIONS):
        get_multi_adapter((ob, req), IResourceDeserializeFromJson)
    end = time.time()
    print(f'Done with {ITERATIONS} in {end - start} seconds')


async def run3():
    lookup_registry = {
        ISecurityInfo: DefaultSecurityInfoAdapter
    }
    ob = test_utils.create_content()
    print('Test manual lookup')
    type_ = type(ob)
    start = time.time()
    for _ in range(ITERATIONS):
        for interface in type_.__implemented__.flattened():
            # this returns in correct order
            if interface in lookup_registry:
                DefaultSecurityInfoAdapter(ob)
    end = time.time()
    print(f'Done with {ITERATIONS} in {end - start} seconds')


async def run():
    await run1()
    await run2()
    await run3()

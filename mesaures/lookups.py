from guillotina.catalog.catalog import DefaultSecurityInfoAdapter
from guillotina.component import getAdapter
from guillotina.component import get_multi_adapter
from guillotina.interfaces import IItem
from guillotina.interfaces import IResourceFieldDeserializer
from guillotina.interfaces import ISecurityInfo
from guillotina.tests import utils as test_utils

import time


ITERATIONS = 1000000


# ----------------------------------------------------
# Measure performance of different types of lookups
#
# Lessons:
#   - Adapters with only 1 lookup aren't much slower than doing your own manual lookup
#   - Each additional thing you're adapting makes your lookup about 1/3 more slow
#   - Keep adapter simple, using callable with params is usually faster and more simple
# ----------------------------------------------------


async def run2(db):
    ob = test_utils.create_content()
    start = time.time()
    for _ in range(ITERATIONS):
        getAdapter(ob, ISecurityInfo)
    end = time.time()
    print(f'Done with {ITERATIONS} in {end - start} seconds')


async def run3(db):
    lookup_registry = {
        ISecurityInfo: DefaultSecurityInfoAdapter
    }
    ob = test_utils.create_content()
    start = time.time()
    type_ = type(ob)
    for _ in range(ITERATIONS):
        for interface in type_.__implemented__.flattened():
            # this returns in correct order
            if interface in lookup_registry:
                DefaultSecurityInfoAdapter(ob)
    end = time.time()
    print(f'Done with {ITERATIONS} in {end - start} seconds')


async def run(db):
    ob = test_utils.create_content()
    req = test_utils.get_mocked_request()
    start = time.time()
    for _ in range(ITERATIONS):
        get_multi_adapter((IItem['title'], ob, req), IResourceFieldDeserializer)
    end = time.time()
    print(f'Done with {ITERATIONS} in {end - start} seconds')

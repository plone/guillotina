from guillotina.component import get_multi_adapter
from guillotina.content import create_content
from guillotina.interfaces import IResourceDeserializeFromJson
from guillotina.tests import mocks
from guillotina.tests.utils import get_mocked_request

import string
import time


ITERATIONS = 1000

# ----------------------------------------------------
# Measure performance of serializing data
#
# Lessons:
#
# ----------------------------------------------------


async def runit(type_name):
    print(f"Test content serialization with {type_name}")
    request = get_mocked_request()
    txn = mocks.MockTransaction()
    ob = await create_content(type_name, id="foobar")
    ob.__txn__ = txn
    deserializer = get_multi_adapter((ob, request), IResourceDeserializeFromJson)
    tags = []
    for l1 in string.ascii_letters:
        tags.append(l1)
        for l2 in string.ascii_letters:
            tags.append(l1 + l2)
            # for l3 in string.ascii_letters:
            #     tags.append(l1 + l2 + l3)
    print(f"{len(tags)} tags")
    data = {
        "title": "Foobar",
        "guillotina.behaviors.dublincore.IDublinCore": {
            "tags": tags,
            "creation_date": "2020-01-02T19:07:48.748922Z",
            "effective_date": "2020-01-02T19:07:48.748922Z",
            "expiration_date": "2020-01-02T19:07:48.748922Z",
            "creators": ["".join(i) for i in zip(string.ascii_letters, string.ascii_letters)],
        },
        "measures.configuration.ITestBehavior1": {"foobar": "123"},
        "measures.configuration.ITestBehavior2": {"foobar": "123"},
        "measures.configuration.ITestBehavior3": {"foobar": "123"},
    }
    start = time.time()
    for _ in range(ITERATIONS):
        await deserializer(data, validate_all=True)
    end = time.time()
    print(f"Done with {ITERATIONS} in {end - start} seconds")


async def run():
    await runit("TestContent1")
    await runit("TestContent6")

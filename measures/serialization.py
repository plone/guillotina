from guillotina.component import get_multi_adapter
from guillotina.content import create_content
from guillotina.interfaces import IResourceDeserializeFromJson
from guillotina.interfaces import IResourceSerializeToJson
from guillotina.tests import mocks
from guillotina.utils import get_current_request

import time


ITERATIONS = 100

# ----------------------------------------------------
# Measure performance of serializing data
#
# Lessons:
#
# ----------------------------------------------------


async def runit(type_name):
    print(f"Test content serialization with {type_name}")
    request = get_current_request()
    txn = mocks.MockTransaction()
    ob = await create_content(type_name, id="foobar")
    ob.__txn__ = txn
    deserializer = get_multi_adapter((ob, request), IResourceDeserializeFromJson)
    data = {
        "title": "Foobar",
        "guillotina.behaviors.dublincore.IDublinCore": {"tags": ["foo", "bar"]},
        "measures.configuration.ITestBehavior1": {"foobar": "123"},
        "measures.configuration.ITestBehavior2": {"foobar": "123"},
        "measures.configuration.ITestBehavior3": {"foobar": "123"},
    }
    await deserializer(data, validate_all=True)
    start = time.time()
    for _ in range(ITERATIONS):
        serializer = get_multi_adapter((ob, request), IResourceSerializeToJson)
        await serializer()
    end = time.time()
    print(f"Done with {ITERATIONS} in {end - start} seconds")


async def run():
    await runit("TestContent1")
    await runit("TestContent6")

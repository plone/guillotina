from guillotina.component import get_multi_adapter
from guillotina.content import create_content
from guillotina.event import notify
from guillotina.events import BeforeObjectAddedEvent
from guillotina.events import ObjectAddedEvent
from guillotina.interfaces import IResourceDeserializeFromJson
from guillotina.tests import mocks
from guillotina.utils import get_current_request

import time


ITERATIONS = 10000

# ----------------------------------------------------
# Measure performance of different types of lookups with different inheritance
# depths and complexity to see if there is a difference in speed
#
# Lessons:
#   - datetimes objects with local tz are slow
#       - switched to use utc datetime objects
#   - dynamically applying interfaces on objects is slow
#       - pre-apply interfaces for behaviors on content
#   - orm.base.BaseObject is overly complex
# ----------------------------------------------------


async def runit(type_name):
    print(f"Test content creation with {type_name}")
    request = get_current_request()
    txn = mocks.MockTransaction()
    container = await create_content(type_name, id="container")
    container.__txn__ = txn
    start = time.time()
    for _ in range(ITERATIONS):
        ob = await create_content(type_name, id="foobar")
        ob.__txn__ = txn
        await notify(BeforeObjectAddedEvent(ob, container, "foobar"))
        deserializer = get_multi_adapter((ob, request), IResourceDeserializeFromJson)
        data = {
            "title": "Foobar",
            "guillotina.behaviors.dublincore.IDublinCore": {"tags": ["foo", "bar"]},
            "measures.configuration.ITestBehavior1": {"foobar": "123"},
            "measures.configuration.ITestBehavior2": {"foobar": "123"},
            "measures.configuration.ITestBehavior3": {"foobar": "123"},
        }
        await deserializer(data, validate_all=True)
        await notify(ObjectAddedEvent(ob, container, "foobar", payload=data))
    end = time.time()
    print(f"Done with {ITERATIONS} in {end - start} seconds")


async def run():
    await runit("TestContent1")
    await runit("TestContent6")

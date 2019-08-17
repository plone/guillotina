from guillotina.component import get_adapter
from guillotina.content import create_content
from guillotina.db.interfaces import IWriter
from guillotina.db.reader import reader

import time


ITERATIONS = 100000


# --------------------------------------------------------
# Measure performance of serialization and deserialization
#
# Lessons:
#   - BaseObject was too complex and unnecessary logic for what we are using.
#       - Simplifying provides 4x speed improvements for deserialization
#       - 2x speed improvements for serializing
# ---------------------------------------------------------


async def run1():
    print("Test serialize content for db")
    ob = await create_content("TestContent6", id="foobar")
    ob.foobar1 = "1"
    ob.foobar2 = "2"
    ob.foobar6 = "6"
    start = time.time()
    writer = get_adapter(ob, IWriter)
    for _ in range(ITERATIONS):
        writer.serialize()
    end = time.time()
    print(f"Done with {ITERATIONS} in {end - start} seconds")


async def run2():
    print("Test deserialize content from db")
    ob = await create_content("TestContent6", id="foobar")
    ob.foobar1 = "1"
    ob.foobar2 = "2"
    ob.foobar6 = "6"
    start = time.time()
    writer = get_adapter(ob, IWriter)
    serialized = writer.serialize()
    for _ in range(ITERATIONS):
        ob = reader({"state": serialized, "zoid": 0, "tid": 0, "id": "foobar"})
    end = time.time()
    assert ob.foobar1 == "1"
    assert ob.foobar6 == "6"
    print(f"Done with {ITERATIONS} in {end - start} seconds")


async def run():
    await run1()
    await run2()

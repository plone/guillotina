from guillotina import configure
from guillotina.component import get_multi_adapter
from guillotina.content import create_content
from guillotina.content import Item
from guillotina.event import notify
from guillotina.events import BeforeObjectAddedEvent
from guillotina.events import ObjectAddedEvent
from guillotina.interfaces import IItem
from guillotina.interfaces import IResourceDeserializeFromJson
from guillotina.tests import mocks
from guillotina.utils import get_current_request

import time


# ----------------------------------------------------
# Measure performance of different types of lookups with different inheritance
# depths and complexity to see if there is a difference in speed
#
# ----------------------------------------------------


ITERATIONS = 10000


class ITestContent1(IItem):
    pass


class ITestContent2(ITestContent1):
    pass

class ITestContent3(ITestContent2):
    pass

class ITestContent4(ITestContent3):
    pass

class ITestContent5(ITestContent4):
    pass

class ITestContent6(ITestContent5):
    pass


@configure.contenttype(
    type_name="TestContent1",
    schema=ITestContent1,
    behaviors=["guillotina.behaviors.dublincore.IDublinCore"])
class TestContent1(Item):
    pass


@configure.contenttype(
    type_name="TestContent6",
    schema=ITestContent6,
    behaviors=["guillotina.behaviors.dublincore.IDublinCore"])
class TestContent6(Item):
    pass


async def runit(type_name):
    print(f'Test content creation with {type_name}')
    request = get_current_request()
    txn = mocks.MockTransaction()
    container = await create_content(type_name, id='container')
    container._p_jar = txn
    start = time.time()
    for _ in range(ITERATIONS):
        ob = await create_content(type_name, id='foobar')
        ob._p_jar = txn
        await notify(BeforeObjectAddedEvent(ob, container, 'foobar'))
        deserializer = get_multi_adapter((ob, request),
                                         IResourceDeserializeFromJson)
        data = {
            'title': 'Foobar',
            'guillotina.behaviors.dublincore.IDublinCore': {
                'tags': ['foo', 'bar']
            }
        }
        await deserializer(data, validate_all=True)
        await notify(ObjectAddedEvent(ob, container, 'foobar', payload=data))
    end = time.time()
    print(f'Done with {ITERATIONS} in {end - start} seconds')


async def run():
    await runit('TestContent1')
    await runit('TestContent6')

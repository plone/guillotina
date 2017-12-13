from guillotina import configure
from guillotina import schema
from guillotina.behaviors.instance import AnnotationBehavior
from guillotina.component import get_multi_adapter
from guillotina.content import create_content
from guillotina.content import Item
from guillotina.event import notify
from guillotina.events import BeforeObjectAddedEvent
from guillotina.events import ObjectAddedEvent
from guillotina.interface import Interface
from guillotina.interfaces import IItem
from guillotina.interfaces import IResourceDeserializeFromJson
from guillotina.tests import mocks
from guillotina.utils import get_current_request

import time


# ----------------------------------------------------
# Measure performance of different types of lookups with different inheritance
# depths and complexity to see if there is a difference in speed
#
# Lessons:
#   - datetimes objects with local tz are slow
#       - switched to use utc datetime objects
#   - dynamically applying interfaces on objects is slow
#       - pre-apply interfaces for behaviors on content
# ----------------------------------------------------


class IMarkerBehavior1(Interface):
    pass

class IMarkerBehavior2(Interface):
    pass

class IMarkerBehavior3(Interface):
    pass

class ITestBehavior1(Interface):
    foobar = schema.TextLine()

class ITestBehavior2(Interface):
    foobar = schema.TextLine()

class ITestBehavior3(Interface):
    foobar = schema.TextLine()


@configure.behavior(
    title="",
    provides=ITestBehavior1,
    marker=IMarkerBehavior1,
    for_="guillotina.interfaces.IResource")
class TestBehavior1(AnnotationBehavior):
    pass


@configure.behavior(
    title="",
    provides=ITestBehavior2,
    marker=IMarkerBehavior2,
    for_="guillotina.interfaces.IResource")
class TestBehavior2(AnnotationBehavior):
    pass


@configure.behavior(
    title="",
    provides=ITestBehavior3,
    marker=IMarkerBehavior3,
    for_="guillotina.interfaces.IResource")
class TestBehavior3(AnnotationBehavior):
    pass


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
    behaviors=[
        "guillotina.behaviors.dublincore.IDublinCore",
        "measures.lookups_interfaces.ITestBehavior1",
        "measures.lookups_interfaces.ITestBehavior2",
        "measures.lookups_interfaces.ITestBehavior3",
    ])
class TestContent1(Item):
    pass


@configure.contenttype(
    type_name="TestContent6",
    schema=ITestContent6,
    behaviors=[
        "guillotina.behaviors.dublincore.IDublinCore",
        "measures.lookups_interfaces.ITestBehavior1",
        "measures.lookups_interfaces.ITestBehavior2",
        "measures.lookups_interfaces.ITestBehavior3",
    ])
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
            },
            'measures.lookups_interfaces.ITestBehavior1': {
                'foobar': '123'
            },
            'measures.lookups_interfaces.ITestBehavior2': {
                'foobar': '123'
            },
            'measures.lookups_interfaces.ITestBehavior3': {
                'foobar': '123'
            }
        }
        await deserializer(data, validate_all=True)
        await notify(ObjectAddedEvent(ob, container, 'foobar', payload=data))
    end = time.time()
    print(f'Done with {ITERATIONS} in {end - start} seconds')


async def run():
    await runit('TestContent1')
    await runit('TestContent6')

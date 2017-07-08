from guillotina import utils
from guillotina.interfaces import IResource
from guillotina.tests.utils import get_mocked_request
from guillotina.tests.utils import get_root

import gc
import json
import resource


def test_module_resolve_path():
    assert utils.resolve_module_path('guillotina') == 'guillotina'
    assert utils.resolve_module_path('guillotina.tests') == 'guillotina.tests'
    assert utils.resolve_module_path('..test_queue') == 'guillotina.tests.test_queue'
    assert utils.resolve_module_path('....api') == 'guillotina.api'


class FooBar(object):
    pass


def test_dotted_name():
    assert utils.get_dotted_name(FooBar()) == 'guillotina.tests.test_utils.FooBar'
    assert utils.get_dotted_name(FooBar) == 'guillotina.tests.test_utils.FooBar'
    assert utils.get_module_dotted_name(FooBar()) == 'guillotina.tests.test_utils'
    assert utils.get_module_dotted_name(FooBar) == 'guillotina.tests.test_utils'
    assert utils.get_dotted_name(IResource) == 'guillotina.interfaces.content.IResource'


async def test_get_content_path(container_requester):
    async with await container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                "@type": "Item",
                "title": "Item1",
                "id": "item1"
            })
        )
        assert status == 201
        request = get_mocked_request(requester.db)
        root = await get_root(request)
        txn = await request._tm.begin(request)
        container = await root.async_get('guillotina')
        obj = await container.async_get('item1')
        assert utils.get_content_path(container) == '/'
        assert utils.get_content_path(obj) == '/item1'
        await request._tm.abort(txn=txn)


async def test_get_content_depth(container_requester):
    async with await container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                "@type": "Item",
                "title": "Item1",
                "id": "item1"
            })
        )
        assert status == 201
        request = get_mocked_request(requester.db)
        root = await get_root(request)
        txn = await request._tm.begin(request)
        container = await root.async_get('guillotina')
        obj = await container.async_get('item1')
        assert utils.get_content_depth(container) == 1
        assert utils.get_content_depth(obj) == 2
        await request._tm.abort(txn=txn)


class TestGetCurrentRequest:
    async def test_gcr_memory(self):
        self.request = get_mocked_request()

        count = 0
        current = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0 / 1024.0
        while True:
            count += 1
            utils.get_current_request()

            if count % 1000000 == 0:
                break

            if count % 100000 == 0:
                gc.collect()
                new = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0 / 1024.0
                if new - current > 10:  # memory leak, this shouldn't happen
                    assert new == current


def test_valid_id():
    assert utils.valid_id('FOObar')
    assert utils.valid_id('FooBAR-_-.')
    assert not utils.valid_id('FooBar-_-.,')
    assert not utils.valid_id('FooBar-_-.@#')
    assert not utils.valid_id('FooBar-_-.?')

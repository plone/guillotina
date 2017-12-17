from guillotina import utils
from guillotina.interfaces import IPrincipalRoleManager
from guillotina.interfaces import IResource
from guillotina.tests.utils import create_content
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
    async with container_requester as requester:
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
    async with container_requester as requester:
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


def test_get_owners(dummy_guillotina):
    content = create_content()
    roleperm = IPrincipalRoleManager(content)
    roleperm.assign_role_to_principal('guillotina.Owner', 'foobar')
    assert utils.get_owners(content) == ['foobar']
    roleperm.assign_role_to_principal('guillotina.Owner', 'foobar2')
    assert utils.get_owners(content) == ['foobar', 'foobar2']


def _test_empty_func():
    return True


def _test_some_args(foo, bar):
    return foo, bar


def _test_some_kwargs(foo=None, bar=None):
    return foo, bar


def _test_some_stars(foo, bar=None, **kwargs):
    return foo, bar, kwargs


def test_lazy_apply():
    assert utils.lazy_apply(_test_empty_func, 'blah', foo='bar')
    assert utils.lazy_apply(_test_some_args, 'foo', 'bar') == ('foo', 'bar')
    assert utils.lazy_apply(_test_some_args, 'foo', 'bar', 'ldkfks', 'dsflk') == ('foo', 'bar')
    assert utils.lazy_apply(_test_some_kwargs, 'foo', bar='bar') == ('foo', 'bar')
    assert utils.lazy_apply(_test_some_kwargs, 'foo', bar='bar', rsdfk='ldskf') == ('foo', 'bar')
    assert (utils.lazy_apply(_test_some_stars, 'foo', 'blah', bar='bar', another='another') ==
            ('foo', 'bar', {'another': 'another'}))


def test_get_random_string():
    utils.get_random_string()


def test_merge_dicts():
    result = utils.merge_dicts({
        'foo': {
            'foo': 2
        }
    }, {
        'bar': 5,
        'foo': {
            'bar': 3
        }
    })
    assert result['foo']['foo'] == 2
    assert result['foo']['bar'] == 3


async def test_get_containers(container_requester):
    async with container_requester as requester:
        request = get_mocked_request(requester.db)
        containers = [c async for c in utils.get_containers(request)]
        assert len(containers) == 1

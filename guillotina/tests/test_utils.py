from guillotina import utils
from guillotina.interfaces import IResource
from guillotina.tests.utils import get_mocked_request
from guillotina.tests.utils import get_root

import json


def test_module_resolve_path():
    assert utils.resolve_module_path('guillotina') == 'guillotina'
    assert utils.resolve_module_path('guillotina.tests') == 'guillotina.tests'
    assert utils.resolve_module_path('..test_queue') == 'guillotina.tests.test_queue'
    assert utils.resolve_module_path('....api') == 'guillotina.api'


class FooBar(object):
    pass


def test_dotted_name():
    assert utils.get_class_dotted_name(FooBar()) == 'guillotina.tests.test_utils.FooBar'
    assert utils.get_class_dotted_name(FooBar) == 'guillotina.tests.test_utils.FooBar'
    assert utils.get_module_dotted_name(FooBar()) == 'guillotina.tests.test_utils'
    assert utils.get_module_dotted_name(FooBar) == 'guillotina.tests.test_utils'
    assert utils.get_class_dotted_name(IResource) == 'guillotina.interfaces.content.IResource'


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
        container = await root.async_get('guillotina')
        obj = await container.async_get('item1')
        assert utils.get_content_path(container) == '/guillotina'
        assert utils.get_content_path(obj) == '/guillotina/item1'

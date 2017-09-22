# -*- encoding: utf-8 -*-
from guillotina.catalog.utils import get_index_fields
from guillotina.content import create_content
from guillotina.interfaces import ICatalogDataAdapter
from guillotina.interfaces import ICatalogUtility
from guillotina.component import queryUtility

import pytest


def test_indexed_fields(dummy_guillotina, loop):
    fields = get_index_fields('Item')
    assert 'type_name' in fields
    assert 'uuid' in fields
    assert 'path' in fields
    assert 'title' in fields
    assert 'creation_date' in fields


@pytest.mark.usefixtures("dummy_request")
class TestCatalog:
    # wrap in test so get_current_request works...
    async def test_get_index_data(self, dummy_request):
        self.request = dummy_request

        container = await create_content(
            'Container',
            id='guillotina',
            title='Guillotina')
        container.__name__ = 'guillotina'

        ob = await create_content('Item', id='foobar')

        data = ICatalogDataAdapter(ob)
        fields = await data()
        assert 'type_name' in fields
        assert 'uuid' in fields
        assert 'path' in fields
        assert 'title' in fields


async def test_registered_base_utility(dummy_request):
    util = queryUtility(ICatalogUtility)
    assert util is not None


async def test_get_data_uses_indexes_param(dummy_request):
    util = queryUtility(ICatalogUtility)
    request = dummy_request  # noqa
    container = await create_content(
        'Container',
        id='guillotina',
        title='Guillotina')
    container.__name__ = 'guillotina'
    ob = await create_content('Item', id='foobar')
    data = await util.get_data(ob, indexes=['title'])
    assert len(data) == 2  # uuid always returned

    data = await util.get_data(ob)
    assert len(data) > 7

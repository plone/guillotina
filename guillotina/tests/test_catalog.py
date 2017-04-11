# -*- encoding: utf-8 -*-
from guillotina.catalog.utils import get_index_fields
from guillotina.content import create_content
from guillotina.interfaces import ICatalogDataAdapter

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

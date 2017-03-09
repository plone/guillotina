# -*- encoding: utf-8 -*-
from guillotina.catalog.utils import get_index_fields
from guillotina.content import create_content
from guillotina.content import create_content_in_container
from guillotina.interfaces import ICatalogDataAdapter
from guillotina.interfaces import IApplication
from guillotina.component import getUtility
import asyncio
from unittest import TestCase
import pytest


def test_indexed_fields(dummy_guillotina, loop):
    fields = get_index_fields('Item')
    assert 'portal_type' in fields
    assert 'uuid' in fields
    assert 'path' in fields
    assert 'title' in fields
    assert 'created' in fields


@pytest.mark.usefixtures("dummy_request")
class TestCatalog:
    # wrap in test so get_current_request works...
    async def test_get_index_data(self, dummy_request):
        self.request = dummy_request

        site = await create_content(
            'Site',
            id='guillotina',
            title='Guillotina')
        site.__name__ = 'guillotina'

        ob = await create_content('Item', id='foobar')

        data = ICatalogDataAdapter(ob)
        fields = await data()
        assert 'portal_type' in fields
        assert 'uuid' in fields
        assert 'path' in fields
        assert 'title' in fields

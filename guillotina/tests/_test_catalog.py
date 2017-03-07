# -*- encoding: utf-8 -*-
from guillotina.catalog.utils import get_index_fields
from guillotina.content import create_content
from guillotina.content import create_content_in_container
from guillotina.interfaces import ICatalogDataAdapter
from guillotina.testing import GuillotinaServerBaseTestCase

import pytest


class TestCatalog(GuillotinaServerBaseTestCase):
    """Functional testing of the API REST."""

    def test_indexed_fields(self):
        fields = get_index_fields('Item')
        self.assertTrue('portal_type' in fields)
        self.assertTrue('uuid' in fields)
        self.assertTrue('path' in fields)
        self.assertTrue('title' in fields)
        self.assertTrue('creation_date' in fields)

    @pytest.mark.asyncio
    async def test_get_index_data(self):
        self.login()
        db = self.new_root()
        site = await create_content(
            'Site',
            id='guillotina',
            title='Guillotina')
        site.__name__ = 'guillotina'
        db['guillotina'] = site
        ob = await create_content_in_container(site, 'Item', 'foobar')

        data = ICatalogDataAdapter(ob)
        fields = await data()
        self.assertTrue('portal_type' in fields)
        self.assertTrue('uuid' in fields)
        self.assertTrue('path' in fields)
        self.assertTrue('title' in fields)

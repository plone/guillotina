# -*- encoding: utf-8 -*-
from plone.server.testing import PloneServerBaseTestCase
from plone.server.catalog.utils import get_index_fields
from plone.server.content import create_content_in_container, create_content
from plone.server.interfaces import ICatalogDataAdapter


class TestCatalog(PloneServerBaseTestCase):
    """Functional testing of the API REST."""

    def test_indexed_fields(self):
        fields = get_index_fields('Item')
        self.assertTrue('portal_type' in fields)
        self.assertTrue('uuid' in fields)
        self.assertTrue('path' in fields)
        self.assertTrue('title' in fields)
        self.assertTrue('creation_date' in fields)

    def test_get_index_data(self):
        self.login()
        db = self.layer.app['plone']
        site = create_content(
            'Site',
            id='plone',
            title='Plone')
        site.__name__ = 'plone'
        db['plone'] = site
        ob = create_content_in_container(site, 'Item', 'foobar')

        data = ICatalogDataAdapter(ob)
        fields = data()
        self.assertTrue('portal_type' in fields)
        self.assertTrue('uuid' in fields)
        self.assertTrue('path' in fields)
        self.assertTrue('title' in fields)

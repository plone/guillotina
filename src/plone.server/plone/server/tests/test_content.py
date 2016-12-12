from plone.server.content import create_content
from plone.server.content import create_content_in_container
from plone.server.content import Folder
from plone.server.content import load_cached_schema
from plone.server.content import NotAllowedContentType
from plone.server.interfaces.types import IConstrainTypes
from plone.server.metaconfigure import contenttype_directive
from plone.server.testing import PloneServerBaseTestCase


class TestContent(PloneServerBaseTestCase):

    def test_allowed_types(self):
        self.login()
        db = self.layer.app['plone']
        site = create_content(
            'Site',
            id='plone',
            title='Plone')
        site.__name__ = 'plone'
        db['plone'] = site

        contenttype_directive(
            self.layer.app.app.config,
            'TestType',
            Folder,
            None,
            behaviors=None,
            add_permission=None,
            allowed_types=['Item'])
        self.layer.app.app.config.execute_actions()
        load_cached_schema()

        obj = create_content_in_container(site, 'TestType', 'foobar')

        constrains = IConstrainTypes(obj, None)
        self.assertEqual(constrains.get_allowed_types(), ['Item'])
        self.assertTrue(constrains.is_type_allowed('Item'))

        with self.assertRaises(NotAllowedContentType):
            create_content_in_container(obj, 'TestType', 'foobar')
        create_content_in_container(obj, 'Item', 'foobar')

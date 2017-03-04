from guillotina import configure
from guillotina.content import create_content
from guillotina.content import create_content_in_container
from guillotina.content import Folder
from guillotina.content import load_cached_schema
from guillotina.content import NotAllowedContentType
from guillotina.interfaces.types import IConstrainTypes
from guillotina.testing import GuillotinaServerBaseTestCase


class TestContent(GuillotinaServerBaseTestCase):

    def test_allowed_types(self):
        self.login()
        db = self.new_root()
        site = create_content(
            'Site',
            id='guillotina',
            title='Guillotina')
        site.__name__ = 'guillotina'
        db['guillotina'] = site

        import guillotina.tests
        configure.register_configuration(Folder, dict(
            portal_type="TestType",
            allowed_types=['Item'],
            module=guillotina.tests  # for registration initialization
        ), 'contenttype')
        configure.load_configuration(
            self.layer.app.app.config, 'guillotina.tests', 'contenttype')
        self.layer.app.app.config.execute_actions()
        load_cached_schema()

        obj = create_content_in_container(site, 'TestType', 'foobar')

        constrains = IConstrainTypes(obj, None)
        self.assertEqual(constrains.get_allowed_types(), ['Item'])
        self.assertTrue(constrains.is_type_allowed('Item'))

        with self.assertRaises(NotAllowedContentType):
            create_content_in_container(obj, 'TestType', 'foobar')
        create_content_in_container(obj, 'Item', 'foobar')

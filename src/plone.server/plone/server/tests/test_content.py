from plone.server.content import createContent
from plone.server.content import createContentInContainer
from plone.server.content import Folder
from plone.server.content import NotAllowedContentType
from plone.server.metaconfigure import contenttypeDirective
from plone.server.testing import PloneServerBaseTestCase


class TestContent(PloneServerBaseTestCase):

    def test_allowed_types(self):
        self.login()
        db = self.layer.app['plone']
        site = createContent(
            'Site',
            id='plone',
            title='Plone')
        site.__name__ = 'plone'
        db['plone'] = site

        contenttypeDirective(
            self.layer.app.app.config,
            'TestType',
            Folder,
            None,
            behaviors=None,
            add_permission=None,
            allowed_types=['Item'])
        self.layer.app.app.config.execute_actions()
        obj = createContentInContainer(site, 'TestType', 'foobar')
        with self.assertRaises(NotAllowedContentType):
            createContentInContainer(obj, 'TestType', 'foobar')
        createContentInContainer(obj, 'Item', 'foobar')

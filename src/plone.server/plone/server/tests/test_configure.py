# -*- encoding: utf-8 -*-
from plone.server.addons import Addon
from zope.interface import Interface
from plone.server import configure
from plone.server.api.service import Service
from plone.server.interfaces import ISite
from plone.server.testing import PloneFunctionalTestCase
from plone.server.content import Item

import json


class TestConfigure(PloneFunctionalTestCase):
    """Functional testing of the API REST."""

    def test_register_service(self):
        cur_count = len(configure.get_services('plone.server.tests'))

        class TestService(Service):
            async def __call__(self):
                return {
                    "foo": "bar"
                }
        configure.register_service(TestService, TestService, dict(
            context=ISite,
            name="@foobar",
            permission='plone.ViewContent'
        ))
        self.assertEqual(len(configure.get_services('plone.server.tests')), cur_count + 1)

        # now test it...
        configure.load_services(self.layer.app.app.config, 'plone.server.tests')
        self.layer.app.app.config.execute_actions()

        resp = self.layer.requester('GET', '/plone/plone/@foobar')
        response = json.loads(resp.text)
        self.assertEqual(response['foo'], 'bar')

    def test_register_contenttype(self):
        cur_count = len(
            configure.get_configurations('plone.server.tests', 'contenttypes'))

        class IMyType(Interface):
            pass

        class MyType(Item):
            pass

        configure.register_configuration(MyType, dict(
            context=ISite,
            schema=IMyType,
            portal_type="MyType1",
            behaviors=["plone.server.behaviors.dublincore.IDublinCore"]
        ), 'contenttypes')
        self.assertEqual(
            len(configure.get_configurations('plone.server.tests', 'contenttypes')),
            cur_count + 1)

        # now test it...
        configure.load_contenttypes(self.layer.app.app.config, 'plone.server.tests')
        self.layer.app.app.config.execute_actions()

        resp = self.layer.requester('GET', '/plone/plone/@types')
        response = json.loads(resp.text)
        self.assertTrue(any("MyType1" in s['title'] for s in response))

    def test_register_behavior(self):
        cur_count = len(configure.get_configurations('plone.server.tests', 'behaviors'))

        from plone.server.interfaces import IFormFieldProvider
        from zope.interface import provider
        from zope import schema

        @provider(IFormFieldProvider)
        class IMyBehavior(Interface):
            foobar = schema.Text()

        configure.behavior(
            title="MyBehavior",
            provides=IMyBehavior,
            factory="plone.behavior.AnnotationStorage",
            for_="plone.server.interfaces.IResource"
        )()

        self.assertEqual(
            len(configure.get_configurations('plone.server.tests', 'behaviors')),
            cur_count + 1)

        class IMyType(Interface):
            pass

        class MyType(Item):
            pass

        configure.register_configuration(MyType, dict(
            context=ISite,
            schema=IMyType,
            portal_type="MyType2",
            behaviors=[IMyBehavior]
        ), 'contenttypes')

        # now test it...
        configure.load_contenttypes(self.layer.app.app.config, 'plone.server.tests')
        self.layer.app.app.config.execute_actions()

        resp = self.layer.requester('GET', '/plone/plone/@types')
        response = json.loads(resp.text)
        type_ = [s for s in response if s['title'] == 'MyType2'][0]
        self.assertTrue('foobar' in type_['definitions']['IMyBehavior']['properties'])

    def test_register_addon(self):
        cur_count = len(configure.get_configurations('plone.server.tests', 'addons'))

        @configure.addon(
            name="myaddon",
            title="My addon")
        class MyAddon(Addon):

            @classmethod
            def install(self, request):
                # install code
                pass

            @classmethod
            def uninstall(self, request):
                # uninstall code
                pass

        self.assertEqual(
            len(configure.get_configurations('plone.server.tests', 'addons')),
            cur_count + 1)

        # now test it...
        configure.load_addons(self.layer.app.app.config, 'plone.server.tests')
        self.layer.app.app.config.execute_actions()

        resp = self.layer.requester('GET', '/plone/plone/@addons')
        response = json.loads(resp.text)
        self.assertTrue('myaddon' in [a['id'] for a in response['available']])

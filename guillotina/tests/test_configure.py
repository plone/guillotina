# -*- encoding: utf-8 -*-
from guillotina import configure
from guillotina.addons import Addon
from guillotina.api.service import Service
from guillotina.content import Item
from guillotina.interfaces import ISite
from guillotina.testing import GuillotinaFunctionalTestCase
from zope.interface import Interface

import json


class TestConfigure(GuillotinaFunctionalTestCase):
    """Functional testing of the API REST."""

    def test_register_service(self):
        cur_count = len(configure.get_configurations('guillotina.tests', 'service'))

        class TestService(Service):
            async def __call__(self):
                return {
                    "foo": "bar"
                }
        configure.register_configuration(TestService, dict(
            context=ISite,
            name="@foobar",
            permission='guillotina.ViewContent'
        ), 'service')

        self.assertEqual(
            len(configure.get_configurations('guillotina.tests', 'service')),
            cur_count + 1)

        # now test it...
        configure.load_configuration(
            self.layer.app.app.config, 'guillotina.tests', 'service')
        self.layer.app.app.config.execute_actions()

        resp = self.layer.requester('GET', '/guillotina/guillotina/@foobar')
        response = json.loads(resp.text)
        self.assertEqual(response['foo'], 'bar')

    def test_register_contenttype(self):
        cur_count = len(
            configure.get_configurations('guillotina.tests', 'contenttype'))

        class IMyType(Interface):
            pass

        class MyType(Item):
            pass

        configure.register_configuration(MyType, dict(
            context=ISite,
            schema=IMyType,
            portal_type="MyType1",
            behaviors=["guillotina.behaviors.dublincore.IDublinCore"]
        ), 'contenttype')

        self.assertEqual(
            len(configure.get_configurations('guillotina.tests', 'contenttype')),
            cur_count + 1)

        # now test it...
        configure.load_configuration(
            self.layer.app.app.config, 'guillotina.tests', 'contenttype')
        self.layer.app.app.config.execute_actions()

        resp = self.layer.requester('GET', '/guillotina/guillotina/@types')
        response = json.loads(resp.text)
        self.assertTrue(any("MyType1" in s['title'] for s in response))

    def test_register_behavior(self):
        cur_count = len(
            configure.get_configurations('guillotina.tests', 'behavior'))

        from guillotina.interfaces import IFormFieldProvider
        from zope.interface import provider
        from zope import schema

        @provider(IFormFieldProvider)
        class IMyBehavior(Interface):
            foobar = schema.Text()

        configure.behavior(
            title="MyBehavior",
            provides=IMyBehavior,
            factory="guillotina.behavior.AnnotationStorage",
            for_="guillotina.interfaces.IResource"
        )()

        self.assertEqual(
            len(configure.get_configurations('guillotina.tests', 'behavior')),
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
        ), 'contenttype')

        # now test it...
        configure.load_configuration(
            self.layer.app.app.config, 'guillotina.tests', 'contenttype')
        self.layer.app.app.config.execute_actions()

        resp = self.layer.requester('GET', '/guillotina/guillotina/@types')
        response = json.loads(resp.text)
        type_ = [s for s in response if s['title'] == 'MyType2'][0]
        self.assertTrue('foobar' in type_['definitions']['IMyBehavior']['properties'])

    def test_register_addon(self):
        cur_count = len(
            configure.get_configurations('guillotina.tests', 'addon'))

        @configure.addon(
            name="myaddon",
            title="My addon")
        class MyAddon(Addon):

            @classmethod
            def install(cls, site, request):
                # install code
                pass

            @classmethod
            def uninstall(cls, site, request):
                # uninstall code
                pass

        self.assertEqual(
            len(configure.get_configurations('guillotina.tests', 'addon')),
            cur_count + 1)

        # now test it...
        configure.load_configuration(
            self.layer.app.app.config, 'guillotina.tests', 'addon')
        self.layer.app.app.config.execute_actions()

        resp = self.layer.requester('GET', '/guillotina/guillotina/@addons')
        response = json.loads(resp.text)
        self.assertTrue('myaddon' in [a['id'] for a in response['available']])

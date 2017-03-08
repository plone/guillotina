# -*- encoding: utf-8 -*-
from guillotina import configure
from guillotina.addons import Addon
from guillotina.api.service import Service
from guillotina.content import Item
from guillotina.interfaces import ISite
from zope.interface import Interface


async def test_register_service(site_requester):
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

    assert len(configure.get_configurations('guillotina.tests', 'service')) == cur_count + 1  # noqa

    async with await site_requester as requester:
        config = requester.root.app.config
        configure.load_configuration(
            config, 'guillotina.tests', 'service')
        config.execute_actions()

        response, status = await requester('GET', '/guillotina/guillotina/@foobar')
        assert response['foo'] == 'bar'


async def test_register_contenttype(site_requester):
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

    assert len(configure.get_configurations('guillotina.tests', 'contenttype')) == cur_count + 1  # noqa

    async with await site_requester as requester:
        config = requester.root.app.config
        # now test it...
        configure.load_configuration(
            config, 'guillotina.tests', 'contenttype')
        config.execute_actions()

        response, status = await requester('GET', '/guillotina/guillotina/@types')
        assert any("MyType1" in s['title'] for s in response)


async def test_register_behavior(site_requester):
    cur_count = len(
        configure.get_configurations('guillotina.tests', 'behavior'))

    from guillotina.interfaces import IFormFieldProvider
    from zope.interface import provider
    from guillotina import schema

    @provider(IFormFieldProvider)
    class IMyBehavior(Interface):
        foobar = schema.Text()

    configure.behavior(
        title="MyBehavior",
        provides=IMyBehavior,
        factory="guillotina.behaviors.instance.AnnotationBehavior",
        for_="guillotina.interfaces.IResource"
    )()

    assert len(configure.get_configurations('guillotina.tests', 'behavior')) == cur_count + 1

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

    async with await site_requester as requester:
        config = requester.root.app.config
        # now test it...
        configure.load_configuration(
            config, 'guillotina.tests', 'contenttype')
        config.execute_actions()

        response, status = await requester('GET', '/guillotina/guillotina/@types')
        type_ = [s for s in response if s['title'] == 'MyType2'][0]
        assert 'foobar' in type_['definitions']['IMyBehavior']['properties']


async def test_register_addon(site_requester):
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

    assert len(configure.get_configurations('guillotina.tests', 'addon')) == cur_count + 1

    async with await site_requester as requester:
        # now test it...
        config = requester.root.app.config
        configure.load_configuration(
            config, 'guillotina.tests', 'addon')
        config.execute_actions()

        response, status = await requester('GET', '/guillotina/guillotina/@addons')
        assert 'myaddon' in [a['id'] for a in response['available']]

from guillotina import configure
from guillotina.addons import Addon
from guillotina.api.service import Service
from guillotina.component import get_utility
from guillotina.content import get_all_possible_schemas_for_type
from guillotina.content import Item
from guillotina.interfaces import IApplication
from guillotina.interfaces import IContainer
from zope.interface import Interface


async def test_register_service(container_requester):
    cur_count = len(configure.get_configurations('guillotina.tests', 'service'))

    class TestService(Service):
        async def __call__(self):
            return {
                "foo": "bar"
            }
    configure.register_configuration(TestService, dict(
        context=IContainer,
        name="@foobar",
        permission='guillotina.ViewContent'
    ), 'service')

    assert len(configure.get_configurations('guillotina.tests', 'service')) == cur_count + 1  # noqa

    async with container_requester as requester:
        config = requester.root.app.config
        configure.load_configuration(
            config, 'guillotina.tests', 'service')
        config.execute_actions()

        response, status = await requester('GET', '/db/guillotina/@foobar')
        assert response['foo'] == 'bar'


async def test_register_contenttype(container_requester):
    cur_count = len(
        configure.get_configurations('guillotina.tests', 'contenttype'))

    class IMyType(Interface):
        pass

    class MyType(Item):
        pass

    configure.register_configuration(MyType, dict(
        context=IContainer,
        schema=IMyType,
        type_name="MyType1",
        behaviors=["guillotina.behaviors.dublincore.IDublinCore"]
    ), 'contenttype')

    assert len(configure.get_configurations('guillotina.tests', 'contenttype')) == cur_count + 1  # noqa

    async with container_requester as requester:
        config = requester.root.app.config
        # now test it...
        configure.load_configuration(
            config, 'guillotina.tests', 'contenttype')
        config.execute_actions()

        response, status = await requester('GET', '/db/guillotina/@types')
        assert any("MyType1" in s['title'] for s in response)


async def test_register_behavior(container_requester):
    cur_count = len(
        configure.get_configurations('guillotina.tests', 'behavior'))

    from guillotina.interfaces import IResource
    from guillotina import schema

    class IMyBehavior(Interface):
        foobar = schema.Text()

    class IMyBehavior2(Interface):
        foobar = schema.Text()

    configure.behavior(
        title="MyBehavior",
        provides=IMyBehavior,
        factory="guillotina.behaviors.instance.AnnotationBehavior",
        for_="guillotina.interfaces.IResource"
    )()
    configure.behavior(
        title="MyBehavior2",
        provides=IMyBehavior2,
        factory="guillotina.behaviors.instance.AnnotationBehavior",
        for_="guillotina.interfaces.IResource"
    )()

    assert len(configure.get_configurations('guillotina.tests', 'behavior')) == cur_count + 2

    class IMyType(IResource):
        pass

    class MyType(Item):
        pass

    configure.register_configuration(MyType, dict(
        context=IContainer,
        schema=IMyType,
        type_name="MyType2",
        behaviors=[IMyBehavior]
    ), 'contenttype')

    root = get_utility(IApplication, name='root')
    config = root.app.config
    # now test it...
    configure.load_configuration(config, 'guillotina.tests', 'contenttype')
    configure.load_configuration(config, 'guillotina.tests', 'behavior')
    config.execute_actions()

    async with container_requester as requester:
        response, status = await requester('GET', '/db/guillotina/@types')
        type_ = [s for s in response if s['title'] == 'MyType2'][0]
        assert 'foobar' in type_['definitions']['IMyBehavior']['properties']

    # also get_all_possible_schemas_for_type should come with this new behavior
    behaviors_schemas = get_all_possible_schemas_for_type('MyType2')
    assert IMyBehavior2 in behaviors_schemas


async def test_register_addon(container_requester):
    cur_count = len(
        configure.get_configurations('guillotina.tests', 'addon'))

    @configure.addon(
        name="myaddon",
        title="My addon")
    class MyAddon(Addon):

        @classmethod
        def install(cls, container, request):
            # install code
            pass

        @classmethod
        def uninstall(cls, container, request):
            # uninstall code
            pass

    assert len(configure.get_configurations('guillotina.tests', 'addon')) == cur_count + 1

    async with container_requester as requester:
        # now test it...
        config = requester.root.app.config
        configure.load_configuration(
            config, 'guillotina.tests', 'addon')
        config.execute_actions()

        response, status = await requester('GET', '/db/guillotina/@addons')
        assert 'myaddon' in [a['id'] for a in response['available']]

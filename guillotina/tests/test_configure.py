from guillotina import configure
from guillotina.addons import Addon
from guillotina.api.service import Service
from guillotina.component import get_utility
from guillotina.component import query_multi_adapter
from guillotina.configure.config import ConfigurationMachine
from guillotina.content import get_all_possible_schemas_for_type
from guillotina.content import Item
from guillotina.event import notify
from guillotina.events import ObjectAddedEvent
from guillotina.factory.app import ApplicationConfigurator
from guillotina.factory.app import configure_application
from guillotina.factory.content import ApplicationRoot
from guillotina.interfaces import IApplication
from guillotina.interfaces import IContainer
from guillotina.tests.utils import create_content
from zope.interface import Interface

import pytest


async def test_register_service(container_requester):
    cur_count = len(configure.get_configurations("guillotina.tests", "service"))

    class TestService(Service):
        async def __call__(self):
            return {"foo": "bar"}

    configure.register_configuration(
        TestService, dict(context=IContainer, name="@foobar", permission="guillotina.ViewContent"), "service"
    )

    assert len(configure.get_configurations("guillotina.tests", "service")) == cur_count + 1  # noqa

    async with container_requester as requester:
        config = requester.root.app.config
        configure.load_configuration(config, "guillotina.tests", "service")
        config.execute_actions()

        response, status = await requester("GET", "/db/guillotina/@foobar")
        assert response["foo"] == "bar"


async def test_register_service_permission(container_requester):
    cur_count = len(configure.get_configurations("guillotina.tests", "service"))

    class TestService(Service):
        async def __call__(self):
            return {"foo": "bar"}

    configure.permission("guillotina.NoBody", "Nobody has access")
    configure.register_configuration(
        TestService, dict(context=IContainer, name="@foobar2", permission="guillotina.NoBody"), "service"
    )

    assert len(configure.get_configurations("guillotina.tests", "service")) == cur_count + 1  # noqa

    async with container_requester as requester:
        config = requester.root.app.config
        configure.load_configuration(config, "guillotina.tests", "service")
        config.execute_actions()

        response, status = await requester("GET", "/db/guillotina/@foobar2")
        assert status == 401


async def test_register_contenttype(container_requester):
    cur_count = len(configure.get_configurations("guillotina.tests", "contenttype"))

    class IMyType(Interface):
        pass

    class MyType(Item):
        pass

    configure.register_configuration(
        MyType,
        dict(
            context=IContainer,
            schema=IMyType,
            type_name="MyType1",
            behaviors=["guillotina.behaviors.dublincore.IDublinCore"],
        ),
        "contenttype",
    )

    assert len(configure.get_configurations("guillotina.tests", "contenttype")) == cur_count + 1  # noqa

    async with container_requester as requester:
        config = requester.root.app.config
        # now test it...
        configure.load_configuration(config, "guillotina.tests", "contenttype")
        config.execute_actions()

        response, status = await requester("GET", "/db/guillotina/@types")
        assert any("MyType1" in s["title"] for s in response)


async def test_register_behavior(container_requester):
    cur_count = len(configure.get_configurations("guillotina.tests", "behavior"))

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
        for_="guillotina.interfaces.IResource",
    )()
    configure.behavior(
        title="MyBehavior2",
        provides=IMyBehavior2,
        factory="guillotina.behaviors.instance.AnnotationBehavior",
        for_="guillotina.interfaces.IResource",
    )()

    assert len(configure.get_configurations("guillotina.tests", "behavior")) == cur_count + 2

    class IMyType(IResource):
        pass

    class MyType(Item):
        pass

    configure.register_configuration(
        MyType,
        dict(context=IContainer, schema=IMyType, type_name="MyType2", behaviors=[IMyBehavior]),
        "contenttype",
    )

    root = get_utility(IApplication, name="root")
    config = root.app.config
    # now test it...
    configure.load_configuration(config, "guillotina.tests", "contenttype")
    configure.load_configuration(config, "guillotina.tests", "behavior")
    config.execute_actions()

    async with container_requester as requester:
        response, status = await requester("GET", "/db/guillotina/@types")
        type_ = [s for s in response if s["title"] == "MyType2"][0]
        assert (
            "foobar"
            in type_["components"]["schemas"]["guillotina.tests.test_configure.IMyBehavior"]["properties"]
        )

    # also get_all_possible_schemas_for_type should come with this new behavior
    behaviors_schemas = get_all_possible_schemas_for_type("MyType2")
    assert IMyBehavior2 in behaviors_schemas


async def test_register_addon(container_requester):
    cur_count = len(configure.get_configurations("guillotina.tests", "addon"))

    @configure.addon(name="myaddon", title="My addon")
    class MyAddon(Addon):
        @classmethod
        def install(cls, container, request):
            # install code
            pass

        @classmethod
        def uninstall(cls, container, request):
            # uninstall code
            pass

    assert len(configure.get_configurations("guillotina.tests", "addon")) == cur_count + 1

    async with container_requester as requester:
        # now test it...
        config = requester.root.app.config
        configure.load_configuration(config, "guillotina.tests", "addon")
        config.execute_actions()

        response, status = await requester("GET", "/db/guillotina/@addons")
        assert "myaddon" in [a["id"] for a in response["available"]]


async def test_view_registered_for_sub_path_matching(dummy_guillotina, dummy_request):
    view = query_multi_adapter((dummy_guillotina.root, dummy_request), name="@match//")
    assert view is not None


async def test_route_match_view(container_requester):
    async with container_requester as requester:
        response, status = await requester("GET", "/@match/foo/bar")
        assert response == {
            "__parts": ["@match", "foo", "bar"],
            "@match": "@match",
            "foo": "foo",
            "bar": "bar",
        }


def test_loading_nested_configuration():
    root = ApplicationRoot(None, None)
    config = ConfigurationMachine()
    root.config = config
    configured = []
    configure_application("guillotina.test_package", config, root, {}, configured)
    assert "guillotina" in configured
    assert "guillotina.test_package" in configured


def test_loading_configuration_does_not_load_subpackage_definition():
    import guillotina
    import guillotina.test_package  # make sure configuration is read

    root = ApplicationRoot(None, None)
    config = ConfigurationMachine()
    root.config = config
    app_configurator = ApplicationConfigurator(["guillotina", "guillotina.test_package"], config, root, {})

    loaded = app_configurator.load_application(guillotina)
    # it should not load sub package configuration
    for _type, configuration in loaded:
        assert "guillotina.test_package" != getattr(configuration.get("klass"), "__module__", None)

    loaded = app_configurator.load_application(guillotina.test_package)
    assert len(loaded) > 0
    # it should not load sub package configuration
    for _type, configuration in loaded:
        assert "guillotina" != getattr(configuration.get("klass"), "__module__", None)


async def test_sync_subscribers_only_called_once(dummy_guillotina):
    parent = create_content()
    ob = create_content(parent=parent)
    event = ObjectAddedEvent(ob, parent, ob.__name__, payload={})
    await notify(event)
    assert event.called == 1


@pytest.mark.app_settings(
    {"foo": "bar", "root_user": {"password": "hi there!"}, "databases": {"db": {"read_only": "yo"}}}
)
async def test_app_settings_are_overwritten_by_pytest_marks(container_requester):
    from guillotina import app_settings

    assert app_settings["foo"] == "bar"
    assert app_settings["root_user"]["password"] == "hi there!"
    assert app_settings["databases"]["db"]["read_only"] == "yo"
    # Check that other keys that were previously there are untouched
    assert "storage" in app_settings["databases"]["db"]


async def test_register_service_with_path(container_requester):
    cur_count = len(configure.get_configurations("guillotina.tests", "service"))

    class TestService(Service):
        async def __call__(self):
            path = self.request.matchdict["filepath"]
            component = self.request.matchdict["component"]
            return {"filepath": path, "component": component}

    configure.register_configuration(
        TestService,
        dict(
            context=IContainer,
            name="@foobar/endpoint/{component}/{filepath:path}",
            permission="guillotina.ViewContent",
        ),
        "service",
    )

    assert len(configure.get_configurations("guillotina.tests", "service")) == cur_count + 1  # noqa

    async with container_requester as requester:
        config = requester.root.app.config
        configure.load_configuration(config, "guillotina.tests", "service")
        config.execute_actions()

        response, status = await requester("GET", "/db/guillotina/@foobar/endpoint/comp1/root/folder/another")
        assert response["filepath"] == "root/folder/another"

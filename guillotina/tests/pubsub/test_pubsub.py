from guillotina.component import get_utility
from guillotina.interfaces import IPubSubUtility

import asyncio
import pytest
import pytest_docker_fixtures


@pytest.mark.app_settings(
    {"applications": ["guillotina", "guillotina.contrib.redis", "guillotina.contrib.pubsub"]}
)
@pytest.mark.asyncio
async def test_pubsub(redis_container, guillotina_main):
    util = get_utility(IPubSubUtility)
    await util.initialize()
    RESULT = []

    async def callback(*, data=None, sender=None):
        RESULT.append(data)

    await util.subscribe("test", "me", callback)

    await util.publish("test", "me", "mydata")

    assert len(RESULT) == 0

    await util.publish("test", "you", "mydata")
    await asyncio.sleep(0.1)

    assert len(RESULT) == 1
    assert RESULT[0] == "mydata"

    await util.publish("test", "you", "mydata")
    await asyncio.sleep(0.1)
    assert len(RESULT) == 2

    await util.unsubscribe("test", "me")

    await util.publish("test", "you", "mydata")
    assert len(RESULT) == 2

    await util.finalize(None)


@pytest.mark.app_settings(
    {"applications": ["guillotina", "guillotina.contrib.redis", "guillotina.contrib.pubsub"]}
)
@pytest.mark.asyncio
async def test_pubsub_recovers_after_restarting_redis(redis_container, guillotina_main):
    from pytest_docker_fixtures.images import settings  # type: ignore

    util = get_utility(IPubSubUtility)
    await util.initialize()
    RESULT = []

    async def callback(*, data=None, sender=None):
        RESULT.append(data)

    await util.subscribe("test", "me", callback)

    await util.publish("test", "me", "mydata")

    assert len(RESULT) == 0

    await util.publish("test", "you", "mydata")
    await asyncio.sleep(0.1)

    assert len(RESULT) == 1
    assert RESULT[0] == "mydata"

    original_options = settings["redis"].get("options", {})
    try:
        _, port = redis_container
        settings["redis"]["options"] = {**original_options, "ports": {"6379/tcp": port}}
        pytest_docker_fixtures.redis_image.stop()
        pytest_docker_fixtures.redis_image.run()
    finally:
        settings["redis"]["options"] = original_options

    await asyncio.sleep(1.1)  # Wait for reconnection

    await util.publish("test", "you", "mydata")
    await asyncio.sleep(0.1)
    assert len(RESULT) == 2

    await util.unsubscribe("test", "me")

    await util.publish("test", "you", "mydata")
    assert len(RESULT) == 2

    await util.finalize(None)

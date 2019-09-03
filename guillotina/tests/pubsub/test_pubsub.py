from guillotina.component import get_utility
from guillotina.interfaces import IPubSubUtility

import asyncio
import pytest


@pytest.mark.app_settings(
    {"applications": ["guillotina", "guillotina.contrib.redis", "guillotina.contrib.pubsub"]}
)
async def test_pubsub(redis_container, guillotina_main, loop):
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

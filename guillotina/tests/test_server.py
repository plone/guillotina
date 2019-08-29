from guillotina.component import get_utility
from guillotina.exceptions import ConflictError
from guillotina.factory.app import close_utilities
from guillotina.test_package import ITestAsyncUtility
from guillotina.traversal import TraversalRouter
from unittest import mock

import asyncio
import pytest


def test_make_app(dummy_guillotina):
    assert dummy_guillotina is not None
    assert type(dummy_guillotina.router) == TraversalRouter


@pytest.mark.asyncio
async def test_trns_retries_with_app(container_requester):
    with mock.patch("guillotina.traversal.BasicMatchInfo.handler") as handle_mock:  # noqa
        f = asyncio.Future()
        f.set_result(None)
        handle_mock.return_value = f
        handle_mock.side_effect = ConflictError()
        async with container_requester as requester:
            _, status = await requester("GET", "/db/guillotina/@types")
            assert status == 409


@pytest.mark.asyncio
async def test_async_util_started_and_stopped(dummy_guillotina):
    util = get_utility(ITestAsyncUtility)
    util.state == "init"

    config_utility = {
        "provides": "guillotina.test_package.ITestAsyncUtility",
        "factory": "guillotina.test_package.AsyncUtility",
        "settings": {},
    }
    dummy_guillotina.root.add_async_utility("test", config_utility)
    util2 = get_utility(ITestAsyncUtility)
    assert util != util2
    # Let the game start
    await asyncio.sleep(0.1)
    assert util2.state == "initialize"
    await close_utilities(dummy_guillotina)
    assert util2.state == "finalize"

from guillotina.testing import ADMIN_TOKEN

import json
import pytest


pytestmark = pytest.mark.asyncio


async def test_hello(guillotina, container_requester):
    async with container_requester as requester:
        headers = {"AUTHORIZATION": "Basic %s" % ADMIN_TOKEN}
        async with requester.client.websocket_connect("db/guillotina/@ws", extra_headers=headers) as ws:
            sending = {
                "op": "GET",
                "value": "/@registry/guillotina.interfaces.registry.ILayers.active_layers",
            }

            await ws.send_str(json.dumps(sending))
            message = await ws.receive_json()
            assert message == {"data": '{"value": []}', "id": "0"}


async def test_send_close(guillotina, container_requester):
    async with container_requester as requester:
        async with requester.client.websocket_connect(
            "db/guillotina/@ws", extra_headers={"AUTHORIZATION": "Basic %s" % ADMIN_TOKEN}
        ) as ws:

            await ws.send_str(json.dumps({"op": "close"}))
            async for msg in ws:  # noqa
                pass


async def test_ws_token(container_requester):
    async with container_requester as requester:
        response, status = await requester("GET", "/db/guillotina/@wstoken")
        assert status == 200
        response, status = await requester(
            "GET", "/db/guillotina?ws_token=" + response["token"], authenticated=False
        )
        assert status == 200

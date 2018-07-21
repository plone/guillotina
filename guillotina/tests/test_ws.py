from guillotina.testing import ADMIN_TOKEN

import aiohttp
import json


async def test_hello(guillotina, container_requester):
    async with container_requester:
        async with aiohttp.ClientSession() as session:
            url = guillotina.server.make_url('db/guillotina/@ws')
            async with session.ws_connect(
                    url,
                    headers={'AUTHORIZATION': 'Basic %s' % ADMIN_TOKEN}) as ws:
                # we should check version
                sending = {
                    'op': 'GET',
                    'value': '/@registry/guillotina.interfaces.registry.ILayers.active_layers'
                }
                await ws.send_str(json.dumps(sending))
                msg = await ws.receive()
                assert msg.type == aiohttp.WSMsgType.text
                message = json.loads(msg.data)
                assert message == {'data': '{"value": []}', 'id': '0'}
                await ws.close()


async def test_send_close(guillotina, container_requester):
    async with container_requester:
        async with aiohttp.ClientSession() as session:
            url = guillotina.server.make_url('db/guillotina/@ws')
            async with session.ws_connect(
                    url,
                    headers={'AUTHORIZATION': 'Basic %s' % ADMIN_TOKEN}) as ws:

                await ws.send_str(json.dumps({'op': 'close'}))
                async for msg in ws:  # noqa
                    pass


async def test_ws_token(container_requester):
    async with container_requester as requester:
        response, status = await requester('GET', '/db/guillotina/@wstoken')
        assert status == 200
        response, status = await requester(
            'GET', '/db/guillotina?ws_token=' + response['token'],
            authenticated=False)
        assert status == 200

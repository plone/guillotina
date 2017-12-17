from guillotina.testing import ADMIN_TOKEN

import aiohttp
import json


async def test_hello(container_requester, loop):
    async with container_requester as requester:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                    'ws://localhost:{port}/db/guillotina/@ws'.format(
                        port=requester.server.port),
                    headers={'AUTHORIZATION': 'Basic %s' % ADMIN_TOKEN}) as ws:
                # we should check version
                sending = {
                    'op': 'GET',
                    'value': '/@registry/guillotina.interfaces.registry.ILayers.active_layers'
                }
                ws.send_str(json.dumps(sending))
                async for msg in ws:
                    if msg.tp == aiohttp.WSMsgType.text:
                        message = json.loads(msg.data)
                        if 'op' in message and message['op'] == 'close':
                            await ws.close()
                            break  # noqa
                        else:
                            assert message == {'value': []}
                            await ws.close()
                    elif msg.tp == aiohttp.WSMsgType.closed:
                        break  # noqa
                    elif msg.tp == aiohttp.WSMsgType.error:
                        break  # noqa
                return {}


async def test_send_close(container_requester, loop):
    async with container_requester as requester:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                    'ws://localhost:{port}/db/guillotina/@ws'.format(
                        port=requester.server.port),
                    headers={'AUTHORIZATION': 'Basic %s' % ADMIN_TOKEN}) as ws:
                ws.send_str(json.dumps({'op': 'close'}))
                async for msg in ws:
                    if msg.tp == aiohttp.WSMsgType.text:
                        pass
                    elif msg.tp == aiohttp.WSMsgType.closed:
                        break  # noqa
                    elif msg.tp == aiohttp.WSMsgType.error:
                        break  # noqa


async def test_ws_token(container_requester, loop):
    async with container_requester as requester:
        response, status = await requester('GET', '/db/guillotina/@wstoken')
        assert status == 200
        response, status = await requester(
            'GET', '/db/guillotina?ws_token=' + response['token'],
            authenticated=False)
        assert status == 200

# -*- coding: utf-8 -*-
from guillotina.testing import ADMIN_TOKEN

import aiohttp
import json


async def test_hello(container_requester, loop):
    async with await container_requester as requester:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                    'ws://localhost:{port}/db/guillotina/@ws'.format(
                        port=requester.server.port),
                    headers={'AUTHORIZATION': 'Basic %s' % ADMIN_TOKEN}) as ws:
                # we should check version
                sending = {
                    'op': 'GET',
                    'value': '/'
                }
                ws.send_str(json.dumps(sending))
                async for msg in ws:
                    if msg.tp == aiohttp.WSMsgType.text:
                        message = json.loads(msg.data)
                        if 'op' in message and message['op'] == 'close':
                            await ws.close()
                            break  # noqa
                        else:
                            assert len(message['items']) == 0
                            await ws.close()
                    elif msg.tp == aiohttp.WSMsgType.closed:
                        break  # noqa
                    elif msg.tp == aiohttp.WSMsgType.error:
                        break  # noqa
                return {}

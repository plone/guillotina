# -*- coding: utf-8 -*-
from plone.server.testing import PloneFunctionalTestCase
from plone.server.testing import TESTING_PORT
from plone.server.testing import ADMIN_TOKEN
import json
import aiohttp
import asyncio


class FunctionalTestServer(PloneFunctionalTestCase):
    """Functional testing of the API REST."""

    def test_hello(self):
        async def hello(self):
            session = aiohttp.ClientSession()
            async with session.ws_connect(
                    'ws://localhost:{port}/plone/plone/@ws'.format(
                        port=TESTING_PORT),
                    headers={'AUTHORIZATION': 'Basic %s' % ADMIN_TOKEN}) as ws:
                # we should check version
                sending = {
                    'op': 'GET',
                    'value': '/'
                }
                ws.send_str(json.dumps(sending))
                async for msg in ws:
                    if msg.tp == aiohttp.MsgType.text:
                        message = json.loads(msg.data)
                        if 'op' in message and message['op'] == 'close':
                            await ws.close()
                            break
                        else:
                            self.assertTrue(len(message['items']) == 0)
                            await ws.close()
                    elif msg.tp == aiohttp.MsgType.closed:
                        break
                    elif msg.tp == aiohttp.MsgType.error:
                        break
                return {}

        loop = asyncio.get_event_loop()
        future = asyncio.run_coroutine_threadsafe(hello(self), loop)
        result = future.result()

# -*- coding: utf-8 -*-
import aiohttp
from aiohttp import web
from plone.server.api.service import Service


class WebsocketsView(Service):
    async def __call__(self):
        ws = web.WebSocketResponse()
        await ws.prepare(self.request)

        async for msg in ws:
            if msg.tp == aiohttp.MsgType.text:
                if msg.data == 'close':
                    await ws.close()
                else:
                    ws.send_str(msg.data + '/answer')
            elif msg.tp == aiohttp.MsgType.error:
                print('ws connection closed with exception %s' %
                      ws.exception())

        print('websocket connection closed')

        return ws

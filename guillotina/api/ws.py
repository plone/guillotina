# -*- coding: utf-8 -*-
from aiohttp import web
from datetime import datetime
from datetime import timedelta
from guillotina import app_settings
from guillotina import configure
from guillotina import jose
from guillotina import logger
from guillotina.api.service import Service
from guillotina.browser import Response
from guillotina.component import getUtility
from guillotina.component import queryMultiAdapter
from guillotina.interfaces import IContainer
from guillotina.interfaces import IInteraction
from guillotina.interfaces import IPermission
from guillotina.interfaces import ITraversableView
from guillotina.transactions import get_tm

import aiohttp
import asyncio
import ujson


@configure.service(
    context=IContainer, method='GET',
    permission='guillotina.AccessContent', name='@wstoken',
    summary='Return a web socket token',
    responses={
        "200": {
            "description": "The new token",
            "schema": {
                "properties": {
                    "token": {
                        "type": "string",
                        "required": True
                    }
                }
            }
        }
    })
class WebsocketGetToken(Service):
    _websockets_ttl = 60

    def generate_websocket_token(self, real_token):
        exp = datetime.utcnow() + timedelta(
            seconds=self._websockets_ttl)

        claims = {
            'iat': int(datetime.utcnow().timestamp()),
            'exp': int(exp.timestamp()),
            'token': real_token
        }
        jwe = jose.encrypt(claims, app_settings['rsa']['priv'])
        token = jose.serialize_compact(jwe)
        return token.decode('utf-8')

    async def __call__(self):
        # Get token
        header_auth = self.request.headers.get('AUTHORIZATION')
        token = None
        if header_auth is not None:
            schema, _, encoded_token = header_auth.partition(' ')
            if schema.lower() == 'basic' or schema.lower() == 'bearer':
                token = encoded_token

        # Create ws token
        new_token = self.generate_websocket_token(token)
        return {
            "token": new_token
        }


@configure.service(
    context=IContainer, method='GET',
    permission='guillotina.AccessContent', name='@ws',
    summary='Make a web socket connection')
class WebsocketsView(Service):

    async def handle_ws_request(self, ws, message):
        method = app_settings['http_methods']['GET']
        path = tuple(p for p in message['value'].split('/') if p)

        # avoid circular import
        from guillotina.traversal import do_traverse

        obj, tail = await do_traverse(
            self.request, self.request.container, path)

        traverse_to = None

        if tail and len(tail) == 1:
            view_name = tail[0]
        elif tail is None or len(tail) == 0:
            view_name = ''
        else:
            view_name = tail[0]
            traverse_to = tail[1:]

        permission = getUtility(
            IPermission, name='guillotina.AccessContent')

        allowed = IInteraction(self.request).check_permission(
            permission.id, obj)
        if not allowed:
            response = {
                'error': 'Not allowed'
            }
            ws.send_str(ujson.dumps(response))

        try:
            view = queryMultiAdapter(
                (obj, self.request), method, name=view_name)
        except AttributeError:
            view = None

        if traverse_to is not None:
            if view is None or not ITraversableView.providedBy(view):
                response = {
                    'error': 'Not found'
                }
                ws.send_str(ujson.dumps(response))
            else:
                try:
                    view = await view.publish_traverse(traverse_to)
                except Exception as e:
                    logger.error(
                        "Exception on view execution",
                        exc_info=e)
                    response = {
                        'error': 'Not found'
                    }
                    ws.send_str(ujson.dumps(response))

        view_result = await view()
        if isinstance(view_result, Response):
            view_result = view_result.response

        # Return the value
        ws.send_str(ujson.dumps(view_result))

        # Wait for possible value
        futures_to_wait = self.request._futures.values()
        if futures_to_wait:
            await asyncio.gather(*list(futures_to_wait))
            self.request._futures = {}

    async def __call__(self):
        tm = get_tm(self.request)
        await tm.abort(self.request)
        ws = web.WebSocketResponse()
        await ws.prepare(self.request)

        async for msg in ws:
            if msg.tp == aiohttp.WSMsgType.text:
                message = ujson.loads(msg.data)
                if message['op'] == 'close':
                    await ws.close()
                elif message['op'] == 'GET':
                    txn = await tm.begin(request=self.request)
                    try:
                        await self.handle_ws_request(ws, message)
                    except Exception:
                        await ws.close()
                        raise
                    finally:
                        # only currently support GET requests which are *never*
                        # supposed to be commits
                        await tm.abort(txn=txn)
                else:
                    await ws.close()
            elif msg.tp == aiohttp.WSMsgType.error:
                logger.debug('ws connection closed with exception {0:s}'
                             .format(ws.exception()))

        logger.debug('websocket connection closed')

        return {}

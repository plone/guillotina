# -*- coding: utf-8 -*-
from aiohttp import web
from plone.server import app_settings
from plone.server import jose
from datetime import datetime
from datetime import timedelta
from plone.server.api.service import Service
from plone.server.browser import Response
from plone.server.interfaces import ITraversableView
from plone.server.traversal import do_traverse
from zope.component import getUtility
from zope.component import queryMultiAdapter
from zope.security.interfaces import IPermission

import aiohttp
import logging
import ujson


logger = logging.getLogger(__name__)


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
                token = encoded_token.encode('ascii')

        # Create ws token
        new_token = self.generate_websocket_token(token)
        return {
            "token": new_token
        }


class WebsocketsView(Service):

    async def __call__(self):
        ws = web.WebSocketResponse()
        await ws.prepare(self.request)

        async for msg in ws:
            if msg.tp == aiohttp.MsgType.text:
                message = ujson.loads(msg.data)
                if message['op'] == 'close':
                    await ws.close()
                elif message['op'] == 'GET':
                    method = app_settings['http_methods']['GET']
                    path = tuple(p for p in message['value'].split('/') if p)
                    obj, tail = await do_traverse(
                        self.request, self.request.site, path)

                    traverse_to = None

                    if tail and len(tail) == 1:
                        view_name = tail[0]
                    elif tail is None or len(tail) == 0:
                        view_name = ''
                    else:
                        view_name = tail[0]
                        traverse_to = tail[1:]

                    permission = getUtility(
                        IPermission, name='plone.AccessContent')

                    allowed = self.request.security.checkPermission(
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
                                view = view.publishTraverse(traverse_to)
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

                    ws.send_str(ujson.dumps(view_result))
                else:
                    await ws.close()
            elif msg.tp == aiohttp.MsgType.error:
                logger.debug('ws connection closed with exception {0:s}'
                             .format(ws.exception()))

        logger.debug('websocket connection closed')

        return {}

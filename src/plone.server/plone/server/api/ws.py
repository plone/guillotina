# -*- coding: utf-8 -*-
from aiohttp import web
from plone.server.api.service import Service
from plone.server.traversal import do_traverse
import logging
import aiohttp
import ujson
from zope.component import getUtility
from zope.security.interfaces import IPermission
from zope.component import queryMultiAdapter
from plone.server import DICT_METHODS
from plone.server.interfaces import ITraversableView
from plone.server.browser import Response



logger = logging.getLogger(__name__)


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
                    method = DICT_METHODS['GET']
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
                    # Site registry lookup
                    try:
                        view = self.request.site_components.queryMultiAdapter(
                            (obj, self.request), method, name=view_name)
                    except AttributeError:
                        view = None

                    # Global registry lookup
                    if view is None:
                        view = queryMultiAdapter(
                            (obj, self.request), method, name=view_name)

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

from aiohttp import web
from guillotina import configure
from guillotina import jose
from guillotina import logger
from guillotina import routes
from guillotina._settings import app_settings
from guillotina.api.service import Service
from guillotina.auth.extractors import BasicAuthPolicy
from guillotina.browser import Response
from guillotina.component import get_adapter
from guillotina.component import get_utility
from guillotina.component import query_multi_adapter
from guillotina.interfaces import IContainer
from guillotina.interfaces import IInteraction
from guillotina.interfaces import IPermission
from guillotina.security.utils import get_view_permission
from guillotina.transactions import get_tm

import aiohttp
import time
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

    def generate_websocket_token(self, real_token, data={}):
        claims = {
            'iat': int(time.time()),
            'exp': int(time.time() + self._websockets_ttl),
            'token': real_token
        }
        claims.update(data)
        jwe = jose.encrypt(claims, app_settings['rsa']['priv'])
        token = jose.serialize_compact(jwe)
        return token.decode('utf-8')

    async def __call__(self):
        # Get token
        header_auth = self.request.headers.get('AUTHORIZATION')
        token = None
        data = {}
        if header_auth is not None:
            schema, _, encoded_token = header_auth.partition(' ')
            if schema.lower() == 'basic':
                # special case, we need to hash passwd here...
                policy = BasicAuthPolicy(self.request)
                extracted = await policy.extract_token(header_auth)
                data['id'] = extracted['id']
                token = extracted['token']
            elif schema.lower() == 'bearer':
                token = encoded_token

        # Create ws token
        new_token = self.generate_websocket_token(token, data)
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

        from guillotina.traversal import traverse
        obj, tail = await traverse(self.request, self.request.container, path)

        if tail and len(tail) > 0:
            # convert match lookups
            view_name = routes.path_to_view_name(tail)
        elif not tail:
            view_name = ''
        else:
            raise

        permission = get_utility(
            IPermission, name='guillotina.AccessContent')

        security = get_adapter(self.request, IInteraction)
        allowed = security.check_permission(permission.id, obj)
        if not allowed:
            return ws.send_str(ujson.dumps({
                'error': 'Not allowed'
            }))

        try:
            view = query_multi_adapter(
                (obj, self.request), method, name=view_name)
        except AttributeError:
            view = None

        try:
            view.__route__.matches(self.request, tail or [])
        except (KeyError, IndexError):
            view = None

        if view is None:
            return ws.send_str(ujson.dumps({
                'error': 'Not found'
            }))

        ViewClass = view.__class__
        view_permission = get_view_permission(ViewClass)
        if not security.check_permission(view_permission, view):
            return ws.send_str(ujson.dumps({
                'error': 'No view access'
            }))

        if hasattr(view, 'prepare'):
            view = (await view.prepare()) or view

        view_result = await view()
        if isinstance(view_result, Response):
            view_result = view_result.response

        # Return the value
        ws.send_str(ujson.dumps(view_result))

        # Wait for possible value
        self.request.execute_futures()

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

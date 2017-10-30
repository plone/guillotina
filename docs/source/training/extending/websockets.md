# Websockets

Websocket support is built-in to Guillotina.

It's as simple as using an `aiohttp` websocket in a service.

Create a `ws.py` file and put the following code in:


```python
from aiohttp import web
from guillotina import configure
from guillotina.component import get_utility
from guillotina.interfaces import IContainer
from guillotina.transactions import get_tm
from guillotina_chat.utility import IMessageSender

import aiohttp
import logging

logger = logging.getLogger('guillotina_chat')


@configure.service(
    context=IContainer, method='GET',
    permission='guillotina.AccessContent', name='@conversate')
async def ws_conversate(context, request):
    ws = web.WebSocketResponse()
    utility = get_utility(IMessageSender)
    utility.register_ws(ws, request)

    tm = get_tm(request)
    await tm.abort(request)
    await ws.prepare(request)

    async for msg in ws:
        if msg.tp == aiohttp.WSMsgType.text:
            # ws does not receive any messages, just sends
            pass
        elif msg.tp == aiohttp.WSMsgType.error:
            logger.debug('ws connection closed with exception {0:s}'
                         .format(ws.exception()))

    logger.debug('websocket connection closed')
    utility.unregister_ws(ws)

    return {}
```


Here, we use the `utility = get_utility(IMessageSender)` to get our async
utility we defined previously. Then we register our webservice with
`utility.register_ws(ws, request)`.

Our web service is simple because we do not need to receive any messages and
the async utility sends out the messages.


## Using websockets

In order to use websockets, you need to request a websocket token first.

```
GET /db/container/@wstoken
Authentication Bearer <jwt token>
```

Then, use this token to generate a webservice URL(JavaScript example here):

```javascript
var url = 'ws://localhost:8080/db/container/@conversate?ws_token=' + ws_token;
SOCKET = new WebSocket(url);
SOCKET.onopen = function(e){
};
SOCKET.onmessage = function(msg){
  var data = JSON.parse(msg.data);
};
SOCKET.onclose = function(e){
};

SOCKET.onerror = function(e){
};
```

# Async Utilities

An async utility is a utility that run persistently on the asyncio event loop.
It is useful for long running tasks.

For our training, we're going to use an async utility with a queue to send
messages to logged in users.

Create a `utility.py` file and put the following code in it.

```python
from guillotina import configure
from guillotina.async import IAsyncUtility
from guillotina.component import getMultiAdapter
from guillotina.interfaces import IResourceSerializeToJsonSummary
from guillotina.renderers import GuillotinaJSONEncoder
from guillotina.utils import get_authenticated_user_id, get_current_request

import asyncio
import json
import logging

logger = logging.getLogger('guillotina_chat')


class IMessageSender(IAsyncUtility):
    pass


@configure.utility(provides=IMessageSender)
class MessageSenderUtility:

    def __init__(self, settings=None, loop=None):
        self._loop = loop
        self._settings = {}
        self._webservices = []

    def register_ws(self, ws, request):
        ws.user_id = get_authenticated_user_id(request)
        self._webservices.append(ws)

    def unregister_ws(self, ws):
        self._webservices.remove(ws)

    async def send_message(self, message):
        summary = await getMultiAdapter(
            (message, get_current_request()),
            IResourceSerializeToJsonSummary)()
        await self._queue.put((message, summary))

    async def initialize(self, app=None):
        self._queue = asyncio.Queue()

        while True:
            try:
                message, summary = await self._queue.get()
                for user_id in message.__parent__.users:
                    for ws in self._webservices:
                        if ws.user_id == user_id:
                            await ws.send_str(json.dumps(
                                summary, cls=GuillotinaJSONEncoder))
            except Exception:
                logger.warn(
                    'Error sending message',
                    exc_info=True)
                await asyncio.sleep(1)
```


Async utilities must implement a `initialize` method and performs the async
task. In our case, it is creating a queue and waiting to process messages
in the queue.

For us, we will send messages to registered websockets.

Make sure, like all other configured moduels, to ensure this file is scanned
by the packages `__init__.py` file.

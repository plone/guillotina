from guillotina.commands import Command
from aiohttp.test_utils import make_mocked_request
from aiohttp.streams import EmptyStreamReader
import asyncio
import sys
import guillotina
import hypercorn


try:
    from aiohttp.web_log import AccessLogger  # type: ignore
except ImportError:
    from aiohttp.helpers import AccessLogger  # type: ignore

try:
    import aiohttp_autoreload
    HAS_AUTORELOAD = True
except ImportError:
    HAS_AUTORELOAD = False


class AsgiStreamReader(EmptyStreamReader):
    def __init__(self, receive):
        self.receive = receive
        self.finished = False

    async def readany(self):
        return await self.read()

    async def read(self):
        if self.finished:
            return b''
        payload = await self.receive()
        self.finished = True
        return payload['body']

async def app1(scope, receive, send):
    if scope["type"] != "http":
        raise Exception("Only the HTTP protocol is supported")

    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [
            (b'content-type', b'text/plain'),
            (b'content-length', b'5'),
        ],
    })
    await send({
        'type': 'http.response.body',
        'body': b'hello',
    })




class HyperCommand(Command):
    description = 'Guillotina server runner'
    profiler = line_profiler = None

    async def __call__(self, scope, receive, send):
        app = None
        assert scope['type'] == 'http'

        import multidict

        headers = multidict.CIMultiDict()

        raw_headers = scope['headers']
        for key, value in raw_headers:
            headers.add(key.decode(), value.decode())

        method = scope['method']
        path = scope['path']
        version = scope['http_version']

        payload = AsgiStreamReader(receive)

        request = make_mocked_request(
            method, path, headers=headers, payload=payload
        )
        request.record = lambda x: None

        request.__class__ = guillotina.request.Request
        r = await app.router.resolve(request)
        resp = await r.handler(request)

        await send({
            'type': 'http.response.start',
            'status': resp.status,
            'headers': [
                [b'content-type', b'text/plain'],
            ]
        })

        await send({
            'type': 'http.response.body',
            'body': resp.text.encode()
        })

    def get_parser(self):
        parser = super(HyperCommand, self).get_parser()
        parser.add_argument('-r', '--reload', action='store_true',
                            dest='reload', help='Auto reload on code changes',
                            default=False)
        parser.add_argument('--port',
                            help='Override port to run this server on',
                            default=None, type=int)
        parser.add_argument('--host',
                            help='Override host to run this server on',
                            default=None)
        return parser


    def run(self, arguments, settings, app):
        if arguments.reload:
            if not HAS_AUTORELOAD:
                sys.stderr.write(
                    'You must install aiohttp_autoreload for the --reload option to work.\n'
                    'Use `pip install aiohttp_autoreload` to install aiohttp_autoreload.\n'
                )
                return 1
            aiohttp_autoreload.start()

        port = arguments.port or settings.get('address', settings.get('port'))
        host = arguments.host or settings.get('host', '0.0.0.0')

        try:
            self.application = app
            config = hypercorn.Config()
            #config.certfile = 'cert.pem'
            config.bind = [f'{host}:{port}']
            #config.keyfile = 'key.pem'

            loop = asyncio.get_event_loop()


            from hypercorn.asyncio import serve
            coro = serve(self, config)
            loop.run_until_complete(coro)
        except asyncio.CancelledError:
            # server shut down, we're good here.
            pass

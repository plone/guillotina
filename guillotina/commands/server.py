from aiohttp import web
from guillotina.commands import Command

import asyncio

try:
    import aiomonitor
    HAS_AIOMONITOR = True
except ImportError:
    HAS_AIOMONITOR = False


class ServerCommand(Command):
    description = 'Guillotina server runner'

    def get_parser(self):
        parser = super(ServerCommand, self).get_parser()
        parser.add_argument('-m', '--monitor', action='store_true',
                            dest='monitor', help='Monitor', default=False)
        return parser

    def run(self, arguments, settings, app):
        port = settings.get('address', settings.get('port'))
        # init monitor just before run_app
        loop = asyncio.get_event_loop()
        if arguments.monitor:
            if not HAS_AIOMONITOR:
                return print('You must install aiomonitor for this option to work')
            with aiomonitor.start_monitor(loop=loop):
                web.run_app(app, host=settings.get('host', '0.0.0.0'), port=port)
        else:
            web.run_app(app, host=settings.get('host', '0.0.0.0'), port=port)

from aiohttp import web
from guillotina.commands import Command

import aiomonitor
import asyncio


class ServerCommand(Command):
    description = 'Guillotina server runner'

    def run(self, arguments, settings, app):
        port = settings.get('address', settings.get('port'))
        # init monitor just before run_app
        loop = asyncio.get_event_loop()
        monitor = settings.get('monitor', False)
        if monitor:
            with aiomonitor.start_monitor(loop=loop):
                web.run_app(app, host=settings.get('host', '0.0.0.0'), port=port)
        else:
            web.run_app(app, host=settings.get('host', '0.0.0.0'), port=port)

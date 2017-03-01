from aiohttp import web
from guillotina.commands import Command


class ServerCommand(Command):
    description = 'Guillotina server runner'

    def run(self, arguments, settings, app):
        port = settings.get('address', settings.get('port'))
        web.run_app(app, host=settings.get('host', '0.0.0.0'), port=port)

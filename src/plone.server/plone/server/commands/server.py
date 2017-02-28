from aiohttp import web
from plone.server.commands import Command


class ServerCommand(Command):
    description = 'Plone server runner'

    def run(self, arguments, settings, app):
        port = settings.get('address', settings.get('port'))
        web.run_app(app, host=settings.get('host', '0.0.0.0'), port=port)

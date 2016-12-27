from aiohttp import web
from plone.server.commands import Command


class ServerCommand(Command):

    def run(self, arguments, settings, app):
        web.run_app(app, port=settings['address'])

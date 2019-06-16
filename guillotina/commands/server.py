import uvicorn
from guillotina.commands import Command


class ServerCommand(Command):
    description = 'Guillotina server runner'
    profiler = line_profiler = None

    def get_parser(self):
        parser = super(ServerCommand, self).get_parser()
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
        port = arguments.port or settings.get('address', settings.get('port'))
        host = arguments.host or settings.get('host', '0.0.0.0')

        uvicorn.run(app, host=host, port=port, reload=arguments.reload)

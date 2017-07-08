from aiohttp import web
from guillotina.commands import Command

import cProfile


try:
    import aiomonitor
    HAS_AIOMONITOR = True
except ImportError:
    HAS_AIOMONITOR = False


try:
    import aiohttp_autoreload
    HAS_AUTORELOAD = True
except ImportError:
    HAS_AUTORELOAD = False


class ServerCommand(Command):
    description = 'Guillotina server runner'

    def get_parser(self):
        parser = super(ServerCommand, self).get_parser()
        parser.add_argument('-m', '--monitor', action='store_true',
                            dest='monitor', help='Monitor', default=False)
        parser.add_argument('-r', '--reload', action='store_true',
                            dest='reload', help='Auto reload on code changes',
                            default=False)
        parser.add_argument('--profile', action='store_true',
                            dest='profile', help='Profile execution',
                            default=False)
        parser.add_argument('--profile-output',
                            help='Where to store the output of the profile data',
                            default=None)
        parser.add_argument('--port',
                            help='Override port to run this server on',
                            default=None, type=int)
        parser.add_argument('--host',
                            help='Override host to run this server on',
                            default=None)
        return parser

    def _run(self, arguments, settings, app):
        port = arguments.port or settings.get('address', settings.get('port'))
        host = arguments.host or settings.get('host', '0.0.0.0')
        if arguments.profile:
            cProfile.runctx("web.run_app(app, host=host, port=port, loop=loop)", {
                'web': web
            }, {
                'port': port,
                'host': host,
                'settings': settings,
                'app': app,
                'loop': self.get_loop()
            }, filename=arguments.profile_output)
        else:
            web.run_app(app, host=host, port=port, loop=self.get_loop())

    def run(self, arguments, settings, app):
        if arguments.monitor:
            if not HAS_AIOMONITOR:
                return print('You must install aiomonitor for the --monitor option to work'
                             'Use `pip install aiomonitor` to install aiomonitor.')
            # init monitor just before run_app
            loop = self.get_loop()
            with aiomonitor.start_monitor(loop=loop):
                self._run(arguments, settings, app)
        if arguments.reload:
            if not HAS_AUTORELOAD:
                return print('You must install aiohttp_autoreload for the --reload option to work'
                             'Use `pip install aiohttp_autoreload` to install aiohttp_autoreload.')
            aiohttp_autoreload.start()

        self._run(arguments, settings, app)

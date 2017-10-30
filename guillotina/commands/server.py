from aiohttp import web
from fnmatch import fnmatch
from guillotina import profile
from guillotina.commands import Command
from guillotina.utils import get_dotted_name

import cProfile
import sys


try:
    import line_profiler
    HAS_LINE_PROFILER = True
except ImportError:
    HAS_LINE_PROFILER = False

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
    profiler = line_profiler = None

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
        parser.add_argument('--line-profiler', action='store_true',
                            dest='line_profiler', help='Line profiler execution',
                            default=False)
        parser.add_argument('--line-profiler-matcher',
                            help='Line profiler execution', default=None)
        parser.add_argument('--line-profiler-output',
                            help='Where to store the output of the line profiler data',
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
        if arguments.line_profiler:
            if not HAS_LINE_PROFILER:
                sys.stderr.write(
                    'You must first install line_profiler for the --line-profiler option to work.'
                    'Use `pip install line_profiler` to install line_profiler.'
                )
                return 1
            self.line_profiler = line_profiler.LineProfiler()
            for func in profile.get_profilable_functions():
                if fnmatch(get_dotted_name(func), arguments.line_profiler_matcher or '*'):
                    self.line_profiler.add_function(func)
            self.line_profiler.enable_by_count()
        if arguments.profile:
            self.profiler = cProfile.Profile()
            self.profiler.runcall(
                web.run_app,
                app, host=host, port=port, loop=self.get_loop(),
                access_log_format=settings.get('access_log_format'))
        else:
            web.run_app(app, host=host, port=port, loop=self.get_loop(),
                        access_log_format=settings.get('access_log_format'))

    def run(self, arguments, settings, app):
        if arguments.monitor:
            if not HAS_AIOMONITOR:
                sys.stderr.write(
                    'You must install aiomonitor for the '
                    '--monitor option to work.\n'
                    'Use `pip install aiomonitor` to install aiomonitor.')
                return 1
            # init monitor just before run_app
            loop = self.get_loop()
            with aiomonitor.start_monitor(loop=loop):
                self._run(arguments, settings, app)
        if arguments.reload:
            if not HAS_AUTORELOAD:
                sys.stderr.write(
                    'You must install aiohttp_autoreload for the --reload option to work.\n'
                    'Use `pip install aiohttp_autoreload` to install aiohttp_autoreload.'
                )
                return 1
            aiohttp_autoreload.start()

        self._run(arguments, settings, app)
        if self.profiler is not None:
            if arguments.profile_output:
                self.profiler.dump_stats(arguments.profile_output)
            else:
                # dump to screen
                self.profiler.print_stats(-1)
        if self.line_profiler is not None:
            self.line_profiler.disable_by_count()
            if arguments.line_profiler_output:
                self.line_profiler.dump_stats(arguments.line_profiler_output)
            else:
                self.line_profiler.print_stats()

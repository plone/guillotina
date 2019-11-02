from aiohttp import web
from guillotina.commands import Command

import asyncio
import sys


try:
    from aiohttp.web_log import AccessLogger  # type: ignore
except ImportError:
    from aiohttp.helpers import AccessLogger  # type: ignore

try:
    import aiohttp_autoreload  # type: ignore

    HAS_AUTORELOAD = True
except ImportError:
    HAS_AUTORELOAD = False


class ServerCommand(Command):
    description = "Guillotina server runner"
    profiler = line_profiler = None

    def get_parser(self):
        parser = super(ServerCommand, self).get_parser()
        parser.add_argument(
            "-r",
            "--reload",
            action="store_true",
            dest="reload",
            help="Auto reload on code changes",
            default=False,
        )
        parser.add_argument("--port", help="Override port to run this server on", default=None, type=int)
        parser.add_argument("--host", help="Override host to run this server on", default=None)
        return parser

    def run(self, arguments, settings, app):
        if arguments.reload:
            if not HAS_AUTORELOAD:
                sys.stderr.write(
                    "You must install aiohttp_autoreload for the --reload option to work.\n"
                    "Use `pip install aiohttp_autoreload` to install aiohttp_autoreload.\n"
                )
                return 1
            aiohttp_autoreload.start()

        port = arguments.port or settings.get("address", settings.get("port"))
        host = arguments.host or settings.get("host", "0.0.0.0")
        log_format = settings.get("access_log_format", AccessLogger.LOG_FORMAT)
        try:
            web.run_app(app, host=host, port=port, access_log_format=log_format)
        except asyncio.CancelledError:
            # server shut down, we're good here.
            pass

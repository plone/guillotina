from guillotina.commands import Command


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
        parser.add_argument("--asgi-server", default="uvicorn", type=str)
        return parser

    async def run(self, arguments, settings, app):
        port = arguments.port or settings.get("address", settings.get("port"))
        host = arguments.host or settings.get("host", "0.0.0.0")
        loggers = settings.get("logging")

        if arguments.asgi_server == "uvicorn":
            from uvicorn import Config  # type: ignore
            from uvicorn import Server  # type: ignore
            from uvicorn.config import LOGGING_CONFIG  # type: ignore

            config = Config(
                app, host=host, port=port, reload=arguments.reload, log_config=loggers or LOGGING_CONFIG
            )
            server = Server(config)
            await server.serve()
        elif arguments.asgi_server == "hypercorn":
            from hypercorn.asyncio import serve  # type: ignore
            from hypercorn.config import Config  # type: ignore
            from hypercorn.logging import CONFIG_DEFAULTS

            config = Config()
            config.bind = [f"{host}:{port}"]
            config.use_reloader = arguments.reload
            config.logconfig_dict = loggers or CONFIG_DEFAULTS
            config.accesslog = "-"
            config.errorlog = "-"
            await serve(app, config)
        else:
            raise Exception(f"Server {arguments.asgi_server} not supported")

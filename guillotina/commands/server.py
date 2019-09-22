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

    def run(self, arguments, settings, app):
        port = arguments.port or settings.get("address", settings.get("port"))
        host = arguments.host or settings.get("host", "0.0.0.0")

        if arguments.asgi_server == "uvicorn":
            import uvicorn

            uvicorn.run(app, host=host, port=port, reload=arguments.reload, access_log=False)
        elif arguments.asgi_server == "hypercorn":
            import asyncio

            from hypercorn.asyncio import serve
            from hypercorn.config import Config

            config = Config()
            config.bind = [f"{host}:{port}"]
            config.use_reloader = arguments.reload
            asyncio.run(serve(app, config))
        else:
            raise Exception(f"Server {arguments.asgi_server} not supported")

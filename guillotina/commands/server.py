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

        parser.add_argument("--http_protocol", help="HTTP protocol auto/h11/httptools on uvicorn", default=None)
        parser.add_argument("--http_keep_alive", help="HTTP keep alive timeout", default=None, type=int)

        parser.add_argument("--asgi-server", default="uvicorn", type=str)
        return parser

    def run(self, arguments, settings, app):
        port = arguments.port or settings.get("address", settings.get("port"))
        host = arguments.host or settings.get("host", "0.0.0.0")

        http_protocol = arguments.http_protocol or settings.get("http_protocol")
        http_keep_alive = arguments.http_keep_alive or settings.get("keep_alive")

        if arguments.asgi_server == "uvicorn":
            import uvicorn  # type: ignore

            config = uvicorn.Config(
                app, http=http_protocol, timeout_keep_alive=int(http_keep_alive),
                host=host, port=port,
                reload=arguments.reload, access_log=False)
            server = uvicorn.Server(config)
            self.loop.run_until_complete(server.serve())

        elif arguments.asgi_server == "hypercorn":
            import asyncio

            from hypercorn.asyncio import serve  # type: ignore
            from hypercorn.config import Config  # type: ignore

            config = Config()
            config.bind = [f"{host}:{port}"]
            config.use_reloader = arguments.reload
            asyncio.run(serve(app, config))
        else:
            raise Exception(f"Server {arguments.asgi_server} not supported")

from guillotina.asgi import AsgiApp
from guillotina.commands import Command
from guillotina.traversal import TraversalRouter

import os
import subprocess
import sys


def create_app():
    config_file = os.getenv("GUILLOTINA_CONFIG_FILE", "config.yaml")
    router = TraversalRouter()
    return AsgiApp(config_file=config_file, settings={}, loop=None, router=router)


app = create_app()


class ServeReloadCommand(Command):
    """
    Command to run the server with reload mode.
    Uses subprocess to ensure clean reloads.
    """

    description = "Serve Guillotina with reload mode"

    def get_parser(self):
        parser = super().get_parser()
        parser.add_argument("--watch", help="Directory to watch for changes", default=".")
        parser.add_argument("--host", help="Host to bind the server to", default="127.0.0.1")
        parser.add_argument("--port", help="Port to bind the server to", type=int, default=8080)
        return parser

    def run(self, arguments, settings, app):
        config_file = arguments.configuration
        if not os.path.exists(config_file):
            print(f"Error: Configuration file not found at '{config_file}'")
            sys.exit(1)

        env = os.environ.copy()
        env["GUILLOTINA_CONFIG_FILE"] = config_file
        module_path = f"{self.__module__}:app"

        command = [
            "uvicorn",
            module_path,
            "--reload",
            f"--reload-dir={arguments.watch}",
            f"--host={arguments.host}",
            f"--port={arguments.port}",
        ]

        try:
            subprocess.run(command, env=env, check=True)
        except FileNotFoundError:
            print("Error: 'uvicorn' command not found.")
            print("Please ensure uvicorn is installed in your environment.")
            sys.exit(1)
        except subprocess.CalledProcessError:
            print("Development server exited with an error.")
        except KeyboardInterrupt:
            print("\nDevelopment server stopped.")

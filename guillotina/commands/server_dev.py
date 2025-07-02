from guillotina.asgi import AsgiApp
from guillotina.commands import Command
from guillotina.traversal import TraversalRouter

import os
import subprocess
import sys


def create_dev_app():
    """
    Create the ASGI application for development with the config file from environment.
    """
    config_file = os.getenv("GUILLOTINA_CONFIG_FILE", "config.yaml")
    router = TraversalRouter()
    return AsgiApp(config_file=config_file, settings={}, loop=None, router=router)


# Create app instance at module level for uvicorn to find
app = create_dev_app()


class ServerDevCommand(Command):
    """
    Command to run the server in development mode with auto-reload.
    Uses subprocess to ensure clean reloads.
    """

    description = "Serve Guillotina in development mode with auto-reload"

    def get_parser(self):
        """
        Parses command-line arguments for the serve-dev command.
        """
        parser = super().get_parser()
        parser.add_argument("--watch", help="Directory to watch for changes", default=".")
        parser.add_argument("--host", help="Host to bind the server to", default="127.0.0.1")
        parser.add_argument("--port", help="Port to bind the server to", type=int, default=8080)
        return parser

    def run(self, arguments, settings, app):
        """
        Run the development server using uvicorn as subprocess for reliable reload.
        """
        config_file = arguments.configuration
        if not os.path.exists(config_file):
            print(f"Error: Configuration file not found at '{config_file}'")
            sys.exit(1)

        print(f"Using configuration file: {config_file}")
        print(f"Watching directory: {arguments.watch}")
        print(f"Server will be available at: http://{arguments.host}:{arguments.port}")

        # Pass the config file path via environment variable
        env = os.environ.copy()
        env["GUILLOTINA_CONFIG_FILE"] = config_file

        # Use the current module as the app entry point
        module_path = f"{self.__module__}:app"

        command = [
            "uvicorn",
            module_path,
            "--reload",
            f"--reload-dir={arguments.watch}",
            f"--host={arguments.host}",
            f"--port={arguments.port}",
        ]

        print(f"Starting development server with command: {' '.join(command)}")

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

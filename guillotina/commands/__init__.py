from guillotina import logger
from guillotina._settings import app_settings
from guillotina.factory import make_app
from guillotina.tests.utils import get_mocked_request
from guillotina.tests.utils import login
from guillotina.utils import resolve_dotted_name

import argparse
import asyncio
import json
import os
import signal
import sys
import yaml


MISSING_SETTINGS = {
    "databases": [{
        "db": {
            "storage": "postgresql",
            "dsn": {
                "scheme": "postgres",
                "dbname": "guillotina",
                "user": "guillotina",
                "host": "localhost",
                "password": "",
                "port": 5432
            },
            "read_only": False
        }
    }],
    "port": 8080,
    "root_user": {
        "password": "root"
    }
}


def get_settings(configuration):
    configuration_filename = configuration
    if configuration == 'config.yaml' and not os.path.exists(configuration):
        # try config.json as well...
        configuration_filename = 'config.json'
    if os.path.exists(configuration_filename):
        with open(configuration_filename, 'r') as config:
            if configuration_filename.lower().endswith('.json'):
                settings = json.load(config)
            else:
                # should be yaml then...
                settings = yaml.load(config)
    else:
        if 'logged' not in MISSING_SETTINGS:
            logger.warning('Could not find the configuration file {}. Using default settings.'.format(
                configuration
            ))
        MISSING_SETTINGS['logged'] = True
        settings = MISSING_SETTINGS.copy()
    return settings


class Command(object):

    description = ''
    hide = False

    def __init__(self):
        '''
        Split out into parts that can be overridden
        '''
        self.setup_fake_request()
        self.parse_arguments()

        settings = get_settings(self.arguments.configuration)
        app = self.make_app(settings)

        self.run_command(app, settings)

    def parse_arguments(self):
        parser = self.get_parser()
        self.arguments = parser.parse_known_args()[0]

    def run_command(self, app, settings):
        if asyncio.iscoroutinefunction(self.run):
            loop = asyncio.get_event_loop()
            # Blocking call which returns when finished
            loop.run_until_complete(self.run(self.arguments, settings, app))
            loop.run_until_complete(self.wait_for_tasks())
            loop.close()
        else:
            self.run(self.arguments, settings, app)

    async def wait_for_tasks(self):
        for task in asyncio.Task.all_tasks():
            if task.done():
                continue
            try:
                if task._coro.__qualname__ in ('Pool.release',):
                    # put known tasks that should be waited on here...
                    logger.info(f'Waiting for {task._coro.__qualname__} to finish')
                    try:
                        await asyncio.wait_for(asyncio.shield(task), 1)
                    except asyncio.TimeoutError:
                        pass
            except (AttributeError, KeyError):
                pass

    def setup_fake_request(self):
        self.request = get_mocked_request()
        login(self.request)

    def get_loop(self):
        return asyncio.get_event_loop()

    def signal_handler(self, signal, frame):
        sys.exit(0)

    def make_app(self, settings):
        signal.signal(signal.SIGINT, self.signal_handler)
        return make_app(settings=settings, loop=self.get_loop())

    def get_parser(self):
        parser = argparse.ArgumentParser(description=self.description)
        parser.add_argument('-c', '--configuration',
                            default='config.yaml', help='Configuration file')
        parser.add_argument('--debug', dest='debug', action='store_true',
                            help='Log verbose')
        parser.set_defaults(debug=False)
        return parser

    def __repr__(self):
        """
        to prevent command line from printing object...
        """
        return ''


def command_runner():
    parser = argparse.ArgumentParser(
        description='Guillotina command runner',
        add_help=False)
    parser.add_argument('command', nargs='?', default='serve')
    parser.add_argument('-c', '--configuration',
                        default='config.yaml', help='Configuration file')
    parser.add_argument('-h', '--help', action='store_true',
                        dest='help', help='Help', default=False)

    arguments, _ = parser.parse_known_args()
    settings = get_settings(arguments.configuration)
    _commands = app_settings['commands'].copy()
    _commands.update(settings.get('commands', {}))
    for module_name in settings.get('applications', []):
        module = resolve_dotted_name(module_name)
        if hasattr(module, 'app_settings') and app_settings != module.app_settings:
            _commands.update(module.app_settings.get('commands', {}))

    if arguments.command == 'serve' and arguments.help:
        # for other commands, pass through and allow those parsers to print help
        parser.print_help()
        return print('''
Available commands:
{}\n\n'''.format('\n  - '.join(c for c in _commands.keys())))

    if arguments.command not in _commands:
        return print('''Invalid command "{}".

Available commands:
{}\n\n'''.format(arguments.command, '\n  - '.join(c for c in _commands.keys())))

    command = resolve_dotted_name(_commands[arguments.command])
    if command is None:
        return print('Could not resolve command {}:{}'.format(
            arguments.command, _commands[arguments.command]
        ))

    # finally, run it...
    command()

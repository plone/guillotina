# -*- coding: utf-8 -*-
from guillotina import logger
from guillotina.factory import make_app
from guillotina.tests.utils import get_mocked_request
from guillotina.tests.utils import login

import argparse
import asyncio
import json
import logging
import os
import sys


MISSING_SETTINGS = {
    "databases": [{
        "db": {
            "storage": "postgresql",
            "type": "postgres",
            "dsn": {
                "scheme": "postgres",
                "dbname": "guillotina",
                "user": "guillotina",
                "host": "localhost",
                "password": "test",
                "port": 5432
            },
            "options": {
                "read_only": False
            }
        }
    }],
    "port": 8080,
    "root_user": {
        "password": "root"
    }
}


class Command(object):

    description = ''

    def __init__(self):
        '''
        Split out into parts that can be overridden
        '''
        self.setup_fake_request()
        self.parse_arguments()

        settings = self.get_settings()
        app = self.make_app(settings)

        self.setup_logging()
        self.run_command(app, settings)

    def parse_arguments(self):
        parser = self.get_parser()
        self.arguments = parser.parse_args()

    def run_command(self, app, settings):
        if asyncio.iscoroutinefunction(self.run):
            loop = asyncio.get_event_loop()
            # Blocking call which returns when finished
            loop.run_until_complete(self.run(self.arguments, settings, app))
            loop.close()
        else:
            self.run(self.arguments, settings, app)

    def setup_fake_request(self):
        self.request = get_mocked_request()
        login(self.request)

    def get_settings(self):
        if os.path.exists(self.arguments.configuration):
            with open(self.arguments.configuration, 'r') as config:
                settings = json.load(config)
        else:
            logger.warn('Could not find the configuration file {}. Using default settings.'.format(
                self.arguments.configuration
            ))
            settings = MISSING_SETTINGS.copy()
        return settings

    def setup_logging(self):
        logging.basicConfig(stream=sys.stdout)
        logger.setLevel(logging.INFO)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        if self.arguments.debug:
            logger.setLevel(logging.DEBUG)
            logging.basicConfig(
                stream=sys.stdout,
                level=logging.DEBUG)
            ch.setLevel(logging.DEBUG)

    def get_loop(self):
        return asyncio.get_event_loop()

    def make_app(self, settings):
        return make_app(settings=settings, loop=self.get_loop())

    def get_parser(self):
        parser = argparse.ArgumentParser(description=self.description)
        parser.add_argument('-c', '--configuration',
                            default='config.json', help='Configuration file')
        parser.add_argument('--debug', dest='debug', action='store_true',
                            help='Log verbose')
        parser.set_defaults(debug=False)
        return parser

    def __repr__(self):
        """
        to prevent command line from printing object...
        """
        return ''

# -*- coding: utf-8 -*-
from plone.server.factory import make_app

import argparse
import json
import logging


logger = logging.getLogger('plone.server')


class Command(object):

    def __init__(self):
        parser = self.get_parser()
        arguments = parser.parse_args()
        app = make_app(config_file=arguments.configuration)

        with open(arguments.configuration, 'r') as config:
            settings = json.load(config)

        if arguments.debug:
            logging.basicConfig(
                level=logging.DEBUG)

        self.run(arguments, settings, app)

    def get_parser(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-c', '--configuration',
                            default='config.json', help='Configuration file')
        parser.add_argument('--debug', dest='debug', action='store_true',
                            help='Log verbose')
        parser.set_defaults(debug=False)
        return parser

# -*- coding: utf-8 -*-
from plone.server.factory import make_app
from plone.server.testing import FakeRequest
from plone.server.testing import TestParticipation

import argparse
import json
import logging
import sys


logger = logging.getLogger('plone.server')


class Command(object):

    def __init__(self):
        self.request = FakeRequest()
        self.request.security.add(TestParticipation(self.request))
        self.request.security.invalidate_cache()
        self.request._cache_groups = {}

        parser = self.get_parser()
        arguments = parser.parse_args()
        app = make_app(config_file=arguments.configuration)

        with open(arguments.configuration, 'r') as config:
            settings = json.load(config)

        logging.basicConfig(stream=sys.stdout)
        logger.setLevel(logging.INFO)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)

        if arguments.debug:
            logger.setLevel(logging.DEBUG)
            logging.basicConfig(
                stream=sys.stdout,
                level=logging.DEBUG)
            ch.setLevel(logging.DEBUG)

        self.run(arguments, settings, app)

    def get_parser(self):
        parser = argparse.ArgumentParser()
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

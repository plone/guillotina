# -*- coding: utf-8 -*-
from aiohttp import web
import plone.server.patch  # noqa
from plone.server.factory import make_app

import argparse
import json
import logging


# logger = logging.getLogger('plone.server')
# logging.basicConfig(
#     level=logging.DEBUG,
#     format='%(threadName)10s %(name)18s: %(message)s',)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--configuration',
                        default='config.json', help='Configuration file')
    parser.add_argument('--debug', dest='debug', action='store_true',
                        help='Log verbose')
    parser.set_defaults(debug=False)
    arguments = parser.parse_args()

    with open(arguments.configuration, 'r') as config:
        settings = json.load(config)

    if arguments.debug:
        logging.basicConfig(
            level=logging.DEBUG)

    web.run_app(make_app(
        config_file=arguments.configuration), port=settings['address'])


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
from aiohttp import web
import plone.server.patch  # noqa
from plone.server.factory import make_app

import argparse
import json
import logging


logger = logging.getLogger('plone.server')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--configuration',
                        default='config.json', help='Configuration file')
    arguments = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(threadName)10s %(name)18s: %(message)s',)

    with open(arguments.configuration, 'r') as config:
        settings = json.load(config)
    web.run_app(make_app(
        config_file=arguments.configuration), port=settings['address'])


if __name__ == '__main__':
    main()

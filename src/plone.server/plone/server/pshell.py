# -*- coding: utf-8 -*-
from zope.component import getUtility
from plone.server import app_settings
from plone.server.factory import make_app
from plone.server.interfaces import IApplication
from plone.server.testing import TESTING_SETTINGS
from code import interact

import argparse
import logging


logger = logging.getLogger('plone.server')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--configuration',
                        default='config.json', help='Configuration file')
    arguments = parser.parse_args()

    app = make_app(config_file=arguments.configuration)
    app_settings['root_user']['password'] = TESTING_SETTINGS['root_user']['password']
    root = getUtility(IApplication, name='root')
    interact('''
plone.server interactive shell
==============================

Available local variables:

    - app
    - root
    - app_settings

''', local={
        'app': app,
        'root': root,
        'app_settings': app_settings
    })


if __name__ == '__main__':
    main()

from code import interact
from guillotina import app_settings
from guillotina.commands import Command
from guillotina.interfaces import IApplication
from guillotina.testing import TESTING_SETTINGS
from guillotina.component import getUtility


class ShellCommand(Command):
    description = 'Guillotina server shell'

    def run(self, arguments, settings, app):
        app_settings['root_user']['password'] = TESTING_SETTINGS['root_user']['password']
        root = getUtility(IApplication, name='root')
        interact('''
guillotina interactive shell
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

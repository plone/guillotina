from code import interact
from plone.server import app_settings
from plone.server.commands import Command
from plone.server.interfaces import IApplication
from plone.server.testing import TESTING_SETTINGS
from zope.component import getUtility


class ShellCommand(Command):
    description = 'Plone server shell'

    def run(self, arguments, settings, app):
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

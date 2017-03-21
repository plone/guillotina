from guillotina import app_settings
from guillotina.commands import Command
from guillotina.component import getUtility
from guillotina.interfaces import IApplication
from guillotina.testing import TESTING_SETTINGS

import aioconsole
import asyncio


class Console(aioconsole.code.AsynchronousConsole):
    async def interact(self, banner=None, stop=True, handle_sigint=True):
        """
        We are now running in loop so we can do async stuff with guillotina
        app and database...
        """
        root = self.locals['root']
        tm = root['db'].get_transaction_manager()
        await tm.begin()
        self.locals['tm'] = tm
        return await super().interact(banner, stop, handle_sigint)


class InteractiveEventLoop(asyncio.SelectorEventLoop):
    """Event loop running a python console."""

    console_class = Console

    def __init__(self, banner=''):
        self.banner = banner
        self.console = None
        self.console_task = None
        self.console_server = None
        super().__init__(selector=None)

    def setup(self, app):
        '''
        need to manually run this after app is initialized and we have
        locals that matter to us...
        '''
        app_settings['root_user']['password'] = TESTING_SETTINGS['root_user']['password']
        root = getUtility(IApplication, name='root')
        _locals = {
            'app': app,
            'root': root,
            'app_settings': app_settings
        }
        self.console = self.console_class(None, locals=_locals, loop=self)
        coro = self.console.interact(self.banner, stop=True, handle_sigint=True)
        self.console_task = asyncio.async(coro, loop=self)

    def close(self):
        if self.console_task and not self.is_running():
            asyncio.Future.cancel(self.console_task)
        super().close()


class ShellCommand(Command):
    description = 'Guillotina server shell'
    loop = None
    banner = '''
guillotina interactive shell
==============================

Available local variables:

    - app
    - root
    - app_settings
    - tm
    - asyncio
    - loop

Example
-------

site = await root['db'].async_get('site')


Commit changes
--------------

If you need to commit changes to db...


await tm.commit()

'''

    def get_loop(self):
        if self.loop is None:
            self.loop = InteractiveEventLoop(self.banner)
            asyncio.set_event_loop(self.loop)
        return self.loop

    def run_command(self, app, settings):
        loop = self.get_loop()
        loop.setup(app)
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass

from guillotina._settings import app_settings
from guillotina.commands import Command
from guillotina.component import get_utility
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
        return await super().interact(banner, stop, handle_sigint)


class ShellHelpers:

    def __init__(self, app, root, request):
        self._app = app
        self._root = root
        self._request = request
        self._active_db = None
        self._active_container = None
        self._active_txn = None
        self._active_tm = None

    async def use_db(self, db_id):
        db = self._root[db_id]
        tm = self._active_tm = db.get_transaction_manager()
        self._request._db_id = db_id
        self._active_db = db
        self._active_txn = await tm.begin()
        self._request._txn = self._active_txn
        self._request._tm = tm
        return self._active_txn

    async def use_container(self, container_id):
        container = await self._active_db.async_get(container_id)
        if container is None:
            raise Exception('Container not found')
        self._request.container = container
        self._request._container_id = container.id
        self._active_container = container
        return container

    async def commit(self):
        if self._active_tm is None:
            raise Exception('No active transaction manager')
        await self._active_tm.commit(txn=self._active_txn)
        self._request.execute_futures()
        self._active_txn = await self._active_tm.begin()
        return self._active_txn

    async def abort(self):
        if self._active_tm is None:
            raise Exception('No active transaction manager')
        await self._active_tm.abort(txn=self._active_txn)
        self._active_txn = await self._active_tm.begin()
        return self._active_txn


class InteractiveEventLoop(asyncio.SelectorEventLoop):  # type: ignore
    """Event loop running a python console."""

    console_class = Console

    def __init__(self, banner='', request=None):
        self.banner = banner
        self.console = None
        self.console_task = None
        self.console_server = None
        self.request = request
        super().__init__(selector=None)

    def setup(self, app):
        '''
        need to manually run this after app is initialized and we have
        locals that matter to us...
        '''
        app_settings['root_user']['password'] = TESTING_SETTINGS['root_user']['password']
        root = get_utility(IApplication, name='root')
        helpers = ShellHelpers(app, root, self.request)
        _locals = {
            'app': app,
            'root': root,
            'app_settings': app_settings,
            'request': self.request,
            'helpers': helpers,
            'use_db': helpers.use_db,
            'use_container': helpers.use_container,
            'commit': helpers.commit,
            'abort': helpers.abort
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
    - request
    - loop
    - use_db
    - use_container
    - commit
    - abort

Example
-------

txn = await use_db('db')
container = await use_container('container')
item = await container.async_get('item')


Commit changes
--------------

If you need to commit changes to db...


tm = root['db'].get_transaction_manager()
txn = await tm.begin()
// do changes...
await tm.commit(txn=txn)

Or, using the helper utilities...

txn = await use_db('db')
container = await use_container('container')
await commit()

'''

    def get_loop(self):
        if self.loop is None:
            self.loop = InteractiveEventLoop(self.banner, self.request)
            asyncio.set_event_loop(self.loop)
        return self.loop

    def run(self, arguments, settings, app):
        loop = self.get_loop()
        loop.setup(app)
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass

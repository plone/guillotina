from guillotina._settings import app_settings
from guillotina.commands import Command
from guillotina.component import get_utility
from guillotina.interfaces import IApplication
from guillotina.testing import TESTING_SETTINGS

import asyncio  # noqa
import sys


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

    def run(self, arguments, settings, app):
        app_settings['root_user']['password'] = TESTING_SETTINGS['root_user']['password']
        root = get_utility(IApplication, name='root')
        helpers = ShellHelpers(app, root, self.request)
        request = self.request  # noqa
        use_db = helpers.use_db  # noqa
        use_container = helpers.use_container  # noqa
        commit = helpers.commit  # noqa
        abort = helpers.abort  # noqa

        try:
            from IPython.terminal.embed import InteractiveShellEmbed
            from traitlets.config.loader import Config
        except ImportError:
            sys.stderr.write(
                'You must install ipython for the '
                'shell command to work.\n'
                'Use `pip install ipython` to install ipython.\n')
            return 1

        cfg = Config()
        ipshell = InteractiveShellEmbed(config=cfg, banner1=self.banner)
        ipshell()

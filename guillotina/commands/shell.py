from guillotina import task_vars
from guillotina import utils
from guillotina._settings import app_settings
from guillotina.commands import Command
from guillotina.component import get_utility
from guillotina.interfaces import IApplication
from guillotina.testing import TESTING_SETTINGS
from guillotina.tests.utils import get_mocked_request
from guillotina.tests.utils import login

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
        db = await utils.get_database(db_id)
        tm = self._active_tm = db.get_transaction_manager()
        self._active_db = db
        self._active_txn = await tm.begin()
        self.setup_context()
        return self._active_txn

    async def use_container(self, container_id):
        with self._active_txn, self._active_tm:
            container = await self._active_db.async_get(container_id)
            if container is None:
                raise Exception("Container not found")
        self._active_container = container
        self.setup_context()
        return container

    async def commit(self):
        if self._active_tm is None:
            raise Exception("No active transaction manager")
        await self._active_tm.commit(txn=self._active_txn)
        self._request.execute_futures()
        self._active_txn = await self._active_tm.begin()
        self.setup_context()
        return self._active_txn

    async def abort(self):
        if self._active_tm is None:
            raise Exception("No active transaction manager")
        await self._active_tm.abort(txn=self._active_txn)
        self._active_txn = await self._active_tm.begin()
        self.setup_context()
        return self._active_txn

    def setup_context(self):
        if self._active_db:
            task_vars.db.set(self._active_db)
            task_vars.tm.set(self._active_db.get_transaction_manager())
        if self._active_txn:
            task_vars.txn.set(self._active_txn)
        if self._active_container:
            task_vars.registry.set(None)
            task_vars.container.set(self._active_container)


class ShellCommand(Command):
    description = "Guillotina server shell"
    loop = None
    banner = """
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
    - utils
    - setup

Example
-------

txn = await use_db('db')
container = await use_container('container')
setup()
item = await container.async_get('item')


Commit changes
--------------

await commit()

Or, abort
---------

await abort()


Configured databases
--------------------

{}

"""

    async def get_banner(self):
        db_ids = []
        async for db in utils.iter_databases():
            db_ids.append("- " + db.id)

        return self.banner.format("\n".join(db_ids))

    def run(self, arguments, settings, app):
        app_settings["root_user"]["password"] = TESTING_SETTINGS["root_user"]["password"]
        root = get_utility(IApplication, name="root")
        request = get_mocked_request()
        login()
        helpers = ShellHelpers(app, root, request)
        task_vars.request.set(request)
        use_db = helpers.use_db  # noqa
        use_container = helpers.use_container  # noqa
        commit = helpers.commit  # noqa
        abort = helpers.abort  # noqa
        setup = helpers.setup_context  # noqa

        try:
            from IPython.terminal.embed import InteractiveShellEmbed  # type: ignore
            from traitlets.config.loader import Config  # type: ignore
        except ImportError:
            sys.stderr.write(
                "You must install ipython for the "
                "shell command to work.\n"
                "Use `pip install ipython` to install ipython.\n"
            )
            return 1

        cfg = Config()
        loop = self.get_loop()
        banner = loop.run_until_complete(self.get_banner())
        ipshell = InteractiveShellEmbed(config=cfg, banner1=banner)
        ipshell()

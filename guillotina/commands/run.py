from guillotina.commands import Command
from guillotina.utils import get_containers
from guillotina.utils import iter_databases
from guillotina.utils import lazy_apply

import importlib.util
import inspect
import logging
import os


logger = logging.getLogger("guillotina")


class RunCommand(Command):
    description = """Run python script.
Your script must have a async run function inside it with params app or container.

Example:

async def run(app):
    pass

Or:

async def run(container):
    pass
"""

    def get_parser(self):
        parser = super(RunCommand, self).get_parser()
        parser.add_argument("-s", "--script", help="script", required=True)
        return parser

    async def run(self, arguments, settings, app):
        script = os.path.abspath(arguments.script)
        spec = importlib.util.spec_from_file_location("module.name", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not hasattr(module, "run"):
            logger.warn(f"Not `async def run()` function found in file {script}")
            return
        sig = inspect.signature(module.run)
        if "container" in sig.parameters:
            async for db in iter_databases():
                # preload dynamic dbs
                pass

            async for txn, tm, container in get_containers():
                await module.run(container)
                await tm.commit(txn=txn)
        else:
            await lazy_apply(module.run, app)

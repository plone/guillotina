from guillotina.commands import Command
from guillotina.component import get_utility
from guillotina.interfaces import IApplication
from guillotina.interfaces import IDatabase


class DatabaseInitializationCommand(Command):
    description = 'Guillotina db initiliazation'

    async def run(self, arguments, settings, app):
        root = get_utility(IApplication, name='root')
        for _id, db in root:
            if IDatabase.providedBy(db):
                print(f'Initializing database: {_id}')
                await db._db._storage.create()

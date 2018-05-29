from guillotina.behaviors.dublincore import IDublinCore
from guillotina.commands import Command
from guillotina.component import get_utility
from guillotina.content import create_content
from guillotina.content import create_content_in_container
from guillotina.event import notify
from guillotina.events import ObjectAddedEvent
from guillotina.interfaces import IApplication
from guillotina.interfaces import IDatabase
from guillotina.interfaces import IPrincipalRoleManager

import aiohttp
import asyncio


class AsyncUrlRetriever:
    '''
    To get urls in a task so we can work on it when we're not writing to the db
    '''

    _max_size = 500

    def __init__(self, api):
        self._api = api
        self._data = []
        self._parsed = []
        self._queue = ['Wisconsin', 'Barcelona', 'Python', 'JavaScript',
                       'Asynchronous I/O', 'Representational state transfer',
                       'JSON', 'PostgreSQL', 'Cockroach Labs']

    async def initialize(self):
        while True:
            if len(self._data) >= self._max_size:
                await asyncio.sleep(0.2)
            elif len(self._queue) > 0:
                # we'll do a batch at a time here...
                async def _parse(page):
                    self._parsed.append(page)
                    self._data.append(await self._api.parse_page(page))

                batch = self._queue[:20]
                self._queue = self._queue[20:]
                await asyncio.gather(*[_parse(p) for p in batch])
            else:
                print('queue empty...')
                await asyncio.sleep(0.2)

    def push(self, title):
        if title not in self._parsed and title not in self._queue:
            self._queue.append(title)

    async def pop(self):
        if len(self._data) == 0:
            print('data 0, manually process one')
            page = self._queue.pop()
            return await self._api.parse_page(page)
        return self._data.pop()


class WikipediaAPI:
    _endpoint = 'https://en.wikipedia.org/w/api.php'
    _base_query = {
        'format': 'json',
        'action': 'query',
        'prop': 'extracts|linkshere',
        'exintro': ''
    }
    _batch_size = 50
    _parsed_count = 0

    def __init__(self):
        self._count = 0
        self._parsed = []  # page ids of already parsed
        self._url_retriever = AsyncUrlRetriever(self)
        self._task = asyncio.ensure_future(self._url_retriever.initialize())

    async def parse_page(self, page):
        self._parsed_count += 1
        # print(f'{self._parsed_count} parsing page {page}')
        params = self._base_query.copy()
        params['titles'] = page
        async with aiohttp.ClientSession() as session:
            async with session.get(self._endpoint, params=params) as resp:
                data = await resp.json()
                return data

    async def parse_pages(self, pages):
        results = []

        async def _parse(page):
            result = await self.parse_page(page)
            if result:
                results.append(result)

        await asyncio.gather(*[_parse(page) for page in pages])
        return results

    async def iter_pages(self):
        '''
        it's wikipedia, we should be able to iterate forever...
        '''

        # get initial page...
        while True:
            data = await self._url_retriever.pop()
            data = data['query']['pages']
            # put everything into a yield queue
            for page_data in data.values():
                links = page_data.get('linkshere', [])
                for link in links:
                    self._url_retriever.push(link['title'].replace('Talk:', ''))
                yield page_data

    def close(self):
        self._task.cancel()


class TestDataCommand(Command):
    description = 'Populate the database with test data'
    _batch_size = 200
    _count = 0

    def get_parser(self):
        parser = super(TestDataCommand, self).get_parser()
        parser.add_argument('--per-node', help='How many items to import per node',
                            type=int, default=30)
        parser.add_argument('--depth', help='How deep to make the nodes',
                            type=int, default=6)
        parser.add_argument('--container', help='Container to put data in',
                            default='testdata')
        return parser

    async def generate_test_data(self, db):
        tm = self.request._tm = db.get_transaction_manager()
        self.request._db_id = db.id
        tm = db.get_transaction_manager()
        self.request._txn = txn = await tm.begin(self.request)

        container = await db.async_get(self.arguments.container)
        if container is None:
            container = await create_content(
                'Container', id=self.arguments.container, title='Test Data')
            container.__name__ = self.arguments.container
            await db.async_set(self.arguments.container, container)
            await container.install()
            self.request._container_id = container.__name__
            # Local Roles assign owner as the creator user
            roleperm = IPrincipalRoleManager(container)
            roleperm.assign_role_to_principal('guillotina.Owner', 'root')

            await notify(ObjectAddedEvent(container, db, container.__name__))
            await tm.commit(txn=txn)
            txn = await tm.begin(self.request)

        self.request.container = container
        self.request._container_id = container.id

        api = WikipediaAPI()
        folder_count = 0
        async for page_data in api.iter_pages():
            await self.import_folder(api, tm, txn, container, page_data)
            folder_count += 1
            if folder_count >= self.arguments.per_node:
                break

        await tm.commit(txn=txn)
        api.close()

    async def import_folder(self, api, tm, txn, folder, page_data, depth=1):
        self._count += 1
        if 'pageid' not in page_data:
            print(f"XXX could not import {page_data['title']}")
            return
        _id = str(page_data['pageid'])
        print(f"{self._count} importing {page_data['title']}")
        obj = await folder.async_get(_id)
        if obj is None:
            obj = await create_content_in_container(
                folder, 'Folder', _id, id=_id,
                creators=('root',), contributors=('root',),
                title=page_data['title'])
        behavior = IDublinCore(obj)
        await behavior.load(create=True)
        behavior.description = page_data.get('extract', '')

        if self._count % self._batch_size == 0:
            await tm.commit(txn=txn)
            await tm.begin(self.request)

        if self.arguments.depth > depth:
            folder_count = 0
            async for page_data in api.iter_pages():
                await self.import_folder(api, tm, txn, obj, page_data, depth + 1)
                folder_count += 1
                if folder_count >= self.arguments.per_node:
                    break

    async def run(self, arguments, settings, app):
        self.arguments = arguments
        root = get_utility(IApplication, name='root')
        for _id, db in root:
            if IDatabase.providedBy(db):
                await self.generate_test_data(db)

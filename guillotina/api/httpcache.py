from zope.interface import Interface
from guillotina.utils import execute
import aiohttp
import asyncio


class IHttpCachePolicyUtility(Interface):
    def __call__(context, request):
        """
        Returns a dictionary with the headers to be added on the response
        """

    async def purge(context):
        """Purges previous responses from all configured proxy servers
        """


class NoHttpCachePolicyUtility:
    def __init__(self, settings, loop=None):
        pass

    def __call__(self, context, request):
        # No headers in this case
        return None

    async def pruge(self, context):
        # Nothing to purge
        return


class SimpleHttpCachePolicyUtility:
    def __init__(self, settings, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self.proxy_servers = settings.get('proxy_servers', [])
        self.max_age = settings.get('max_age')
        self.public = settings.get('public', False)

    def get_etag(self, context):
        # TODO: get tid from context vars
        tid = 'foo'
        uuid = getattr(context, "uuid", '0')  # 0 for app root object
        return f'{uuid}/{tid}'

    def __call__(self, context, request):
        cache_control = 'no-cache'
        if self.max_age:
            cache_control = f'max-age={self.max_age}'
        publicstr = 'public' if self.public else 'private'
        cache_control += f', {publicstr}'
        return {
            'Cache-Control': cache_control,
            "ETag": self.get_etag(context)
        }

    async def purge(self, context):
        execute.in_pool(
            self._real_purge,
            context).after_request()

    async def _real_purge(self, context):
        async with aiohttp.ClientSession() as session:
            tasks = []
            for pserver in self.proxy_servers:
                task = self.purge_from_proxy(pserver, context, session)
                tasks.append(task)
            # Wait for tasks to finish
            await asyncio.gather(*tasks)

    def purge_from_proxy(self, proxy, context, session):
        task = asyncio.ensure_future(
            self._purge_from_proxy(proxy, context, session),
            loop=self.loop)
        return task

    async def _purge_from_proxy(self, proxy, context, session):
        # TODO: get absolute url from context
        url = f'http://{proxy}/{context.url}'
        async with session.purge(url) as resp:
            if resp.status != 200:
                raise Exception('Unable to purge')

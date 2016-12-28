from plone.server.api.service import Service
from plone.server.browser import Response


class ExampleService(Service):

    async def __call__(self):
        return Response({
            'foo': 'bar'
        })

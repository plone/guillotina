from plone.server import configure
from plone.server.api.service import Service
from plone.server.browser import Response
from plone.server.interfaces import ISite


@configure.service(context=ISite, method='POST', permission='plone.AccessContent')
class ExampleService(Service):

    async def __call__(self):
        return Response({
            'foo': 'bar'
        })

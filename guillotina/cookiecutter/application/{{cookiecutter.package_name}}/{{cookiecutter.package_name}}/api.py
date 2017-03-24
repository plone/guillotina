from guillotina import configure
from guillotina.api.service import Service
from guillotina.browser import Response
from guillotina.interfaces import IContainer


@configure.service(context=IContainer, method='POST', name='@foobar',
                   permission='guillotina.AccessContent')
class ExampleService(Service):

    async def __call__(self):
        return Response({
            'foo': 'bar'
        })

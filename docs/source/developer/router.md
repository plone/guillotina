# Router

Guillotina uses `aiohttp` for it's webserver. In order to route requests against
Guillotina's traversal url structure, Guillotina provides it's own router
that does traversal: `guillotina.traversal.router`.

## How URLs are routed

Guillotina's content is structured like a file system. Objects are routed to
URL paths. HTTP verbs are provided against those objects on those paths.
Additional services(or views depending on terminology) are provided with
URL path parts that start with `@`, for example, the `@move` endpoint.

## Route matching

With Guillotina, you can also route custom sub paths off a registered service.
Guillotina is primarily for routing objects to urls; however, this feature is
used to provide additional parameters to the service.

An example of where this is used is for file services: `/db/container/item/@upload/file`.

### Registering custom route parts


```python
from guillotina import configure
@configure.service(
    method='GET', permission='guillotina.AccessContent',
    name='@match/{foo}/{bar}')
async def matching_service(context, request):
    return request.matchdict  # will return {'foo': 'foo', 'bar': 'bar'}
```

Some caveats need to be considered when mixing in routing:

- matches are only done when traversal misses
- there are limits to the variability of the route scheme you use. For example
  `@foobar/{one}/{two}` and `@foobar/one/two` will be converted into the same
  service registration; however, the former will match against variable paths
  and the later will only match `@foobar/one/two`. So you might run into
  restrictions quickly if you're trying to do complex routing.


## Providing your own router

Guillotina allows you to provide your own customized router using the `router`
settings.

Here is an example router that provides `/v1` and `/v2` type url structure:

```python
from guillotina import configure
from guillotina.content import Resource
from guillotina.interfaces import IContainer
from guillotina.interfaces import IDefaultLayer
from guillotina.interfaces import IRequest
from guillotina.interfaces import IResource
from guillotina.traversal import TraversalRouter
from guillotina.traversal import traverse
from zope.interface import alsoProvides


class IV1Layer(IDefaultLayer):
    pass


class IV2Layer(IDefaultLayer):
    pass


@configure.service(method='GET', name='@foobar',
                   permission='guillotina.AccessContent',
                   layer=IV1Layer)
async def v1_service(context, request):
    return {
        'version': '1'
    }


@configure.service(method='GET', name='@foobar',
                   permission='guillotina.AccessContent',
                   layer=IV2Layer)
async def v2_service(context, request):
    return {
        'version': '2'
    }


@configure.contenttype(type_name="VersionRouteSegment")
class VersionRouteSegment(Resource):

    type_name = 'VersionRouteSegment'

    def __init__(self, name, parent):
        super().__init__()
        self.__name__ = self.id = name
        self.__parent__ = parent


class MyRouter(TraversalRouter):
    async def traverse(self, request: IRequest) -> IResource:
        resource, tail = await super().traverse(request)
        if len(tail) > 0 and tail[0] in ('v1', 'v2') and IContainer.providedBy(resource):
            segment = VersionRouteSegment(tail[0], resource)
            if tail[0] == 'v1':
                alsoProvides(request, IV1Layer)
            elif tail[0] == 'v2':
                alsoProvides(request, IV2Layer)

            if len(tail) > 1:
                # finish traversal from here
                return await traverse(request, segment, tail[1:])
            else:
                resource = segment
                tail = tail[1:]
        return resource, tail


app_settings = {
    # provide custom application settings here...
    'router': MyRouter
}
```

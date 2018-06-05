# Response rendering

Guillotina has a rendering framework to be able to dynamically handle multiple
request Accept headers.

Out of the box, Guillotina only supports `application/json`, `text/html` and `text/plain`
dynamic response types. Streaming and web socket type responses are also supported
but are not handled by the dyanamic rendering framework.


## Customizing responses

Services can provide simple type values for responses. Ideally anything that can be
serialized as json(default renderer).

Additionally, services can provide custom response objects to customize status and header.


```python
from guillotina import configure
from guillotina.interfaces import IResource
from guillotina.response import Response

@configure.service(
    context=IResource, name='@custom-status',
    method='GET', permission='guillotina.Public',
    allow_access=True)
async def custom_status(context, request):
    return {'foo': 'bar'}, 201


@configure.service(
    context=IResource, name='@custom-headers',
    method='GET', permission='guillotina.Public',
    allow_access=True)
async def custom_headers(context, request):
    return Response(content={'foo': 'bar'}, status=200, headers={'X-Foobar', 'foobar'})

```


### Response types

Guillotina will automatically transform any response types in the `guillotina.response`
library.

These response objects should have simple dict values for their content if provided.


### Bypassing reponses rendering

If you return any aiohttp based response objects, they will be ignored by the rendering
framework.

This is useful when streaming data for example and it should not be transformed.


### Custom rendering

It's also very easy to provide your own renderer. All you need to do is provide your
own renderer class and configure it with the configuration object.

Here is a yaml example:


```python
from guillotina import configure
from guillotina.renderer import Renderer
import yaml

# yaml is known to have a lot of different content types, it's okay!
@configure.renderer(name='text/vnd.yaml')
@configure.renderer(name='application/yaml')
@configure.renderer(name='application/x-yaml')
@configure.renderer(name='text/x-yaml')
@configure.renderer(name='text/yaml')
class RendererYaml(Renderer):
    content_type = 'application/yaml'

    def get_body(self, value) -> bytes:
        if value is not None:
            value = yaml.dump(value)
            return value.encode('utf-8')
```

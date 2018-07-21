# Application Configuration

`guillotina` handles application configuration mostly with decorators.

For example, registering a new service uses our configuration decorator syntax:

```python
from guillotina import configure
from guillotina.interfaces import IContainer

@configure.service(context=IContainer, name='@myservice', method='GET',
                   permission='guillotina.AccessContent')
async def my_service(context, request):
    return {
        'foo': 'bar'
    }
```

`guillotina` applications can override default `guillotina` configuration.

If multiple `guillotina` applications configure conflicting configurations,
`guillotina` chooses the configuration according to the order the `guillotina`
applications that are included.

A [full reference of the available configure decorators](../../api/configure.html)
can be found in the
[programming api reference section](../../api/index.html).
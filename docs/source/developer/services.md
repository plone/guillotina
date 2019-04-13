# Services

Services provide responses to API endpoint requests. A service is the same as
a "view" that you might see in many web frameworks.

The reason we're using the convention "service" is because we're focusing on
creating API endpoints.


## Defining a service

A service can be as simple as a function in your application:

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

The most simple way to define a service is to use the decorator method shown here.

As long as your application imports the module where your service is defined,
your service will be loaded for you.

In this example, the service will apply to a GET request against a container,
`/zodb/guillotina/@myservice`.


```eval_rst
.. include:: ./_scanning.rst
```


## Class-based services

For more complex services, you might want to use class-based services.

With the class-based approach, the example above will look like this:

```python
from guillotina import configure
from guillotina.interfaces import IContainer
from guillotina.api.service import Service

@configure.service(context=IContainer, name='@myservice', method='GET',
                   permission='guillotina.AccessContent')
class MyService(Service):
    async def __call__(self):
        return {
            'foo': 'bar'
        }
```

## Special cases

### I want that my service is accessible no matter the content

You can define in the service configuration with `allow_access=True`
which tells the security checker to ignore checking for the default
permission `guillotina.AccessContent`.


```python
from guillotina import configure
from guillotina.interfaces import IResource
@configure.service(
    context=IResource, name='@download',
    method='GET', permission='guillotina.Public',
    allow_access=True)
async def my_service(context, request):
    pass
```

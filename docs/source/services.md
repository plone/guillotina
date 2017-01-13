# Services

Services provide responses to api endpoint requests. A service is the same as
a "view" that you might see in many web frameworks.

The reason we're using the convention "service" is because we're focusing on
creating API endpoints.


## Defining a service

A service can be as simple as a function in your application:

```python
from plone.server import configure
from plone.server.interfaces import ISite

@configure.service(context=ISite, name='@myservice', method='GET',
                   permission='plone.AccessContent')
async def my_service(context, request):
    return {
        'foo': 'bar'
    }
```

The most simple way to define a service is to use the decorator method shown here.

As long as your application imports the module where your service is defined,
your service will be loaded for you.

In this example, the service will apply to a GET request against a site,
`/zodb/plone/@myservice`.


**Scanning**
If your service modules are not imported at run-time, you may need to provide an
additional scan call to get your services noticed by `plone.server`.

In your application `__init__.py` file, you can simply provide a `scan` call.

```python
from plone.server import configure

def includeme(root):
    configure.scan('my.package.services')
```


## class based services

For more complex services, you might want to use class based services.

The example above, with the class based approach will look like:

```python
from plone.server import configure
from plone.server.interfaces import ISite
from plone.server.api.service import Service


@configure.service(context=ISite, name='@myservice', method='GET',
                   permission='plone.AccessContent')
class DefaultGET(Service):
    async def __call__(self):
      # self.context
      # self.request
      return {
          'foo': 'bar'
      }

```

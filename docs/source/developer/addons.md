# Add-ons

Addons are integrations that can be installed or uninstalled against a Guillotina container.
`guillotina` applications can potentially provide many addons. If you have
not read the section on applications, please read that before you come here. The
only way to provide addons is to first implement a `guillotina` application.


## Creating an add-on

Create an addon installer class in an `install.py` file in your `guillotina` application:

```python

from guillotina.addons import Addon
from guillotina import configure

@configure.addon(
    name="myaddon",
    title="My addon",
    dependencies=['cms'])
class MyAddon(Addon):

    @classmethod
    def install(cls, container, request):
        # install code
        pass

    @classmethod
    def uninstall(cls, container, request):
        # uninstall code
        pass
```

```eval_rst
.. include:: ./_scanning.rst
```

## Layers

A Layer is a marker you install with your add-on, this allows your application 
to lookup views and adapters (override core functionality) only for the container
you installed the add-on. 


```python

from guillotina.addons import Addon
from guillotina import configure
from guillotina.interfaces import ILayers

LAYER = 'guillotina_myaddon.interfaces.ILayer'

@configure.addon(
    name="myaddon",
    title="My addon")
class MyAddon(Addon):

    @classmethod
    def install(cls, container, request):
        registry = request.container_settings
        registry.for_interface(ILayers).active_layers |= {
            LAYER
        }

    @classmethod
    def uninstall(cls, container, request):
        registry = request.container_settings
        registry.for_interface(ILayers).active_layers -= {
            LAYER
        }
```

## Installing an addon into a container

Addons can be installed into a container using `@addons` endpoint by providing
addon name as `id` For example:

```eval_rst
..  http:example:: curl wget httpie python-requests

    POST /db/container/@addons HTTP/1.1
    Accept: application/json
    Authorization: Basic cm9vdDpyb290
    Content-Type: application/json
    Host: localhost:8080

    {
        "id": "myaddon"
    }


    HTTP/1.1 200 OK
    Content-Type: application/json

    {
        "available": [
            {
                "id": "myaddon",
                "title": "Guillotina DB Users"
            },
            {
                "id": "application_name",
                "title": "Your application title"
            }
        ],
        "installed": [
            "dbusers",
            "application_name"
        ]
    }
```

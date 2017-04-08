# Add-ons

Addons are integrations that can be installed or uninstalled against a Guillotina container.
`guillotina` applications can provide potentially many addons. If you have
not read the section on applications, please read that before you come here. The
only way to provide addons is to first implement a `guillotina` application.


## Creating an add-on

Create an addon installer class in an `install.py` file in your `guillotina` application:

```python

from guillotina.addons import Addon
from guillotina import configure

@configure.addon(
    name="myaddon",
    title="My addon")
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

**Scanning**
If your service modules are not imported at run-time, you may need to provide an
additional scan call to get your services noticed by `guillotina`.

In your application `__init__.py` file, you can simply provide a `scan` call.

```python
from guillotina import configure

def includeme(root):
    configure.scan('my.package.addon')
```


## Layers

Your addon can also install layers for your application to lookup views and adapters
from:

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

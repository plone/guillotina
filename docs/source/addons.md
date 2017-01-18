# Add-ons

Addons are integrations that can be installed or uninstalled against a Plone site.
`plone.server` applications can provide potentially many addons. If you have
not read the section on applications, please read that before you come here. The
only way to provide addons is to first implement a `plone.server` application.


## Creating an add-on

Create an addon installer class in an `install.py` file in your `plone.server` application:

```python

from plone.server.addons import Addon
from plone.server import configure

@configure.addon(
    name="myaddon",
    title="My addon")
class MyAddon(Addon):

    @classmethod
    def install(self, request):
        # install code
        pass

    @classmethod
    def uninstall(self, request):
        # uninstall code
        pass
```

**Scanning**
If your service modules are not imported at run-time, you may need to provide an
additional scan call to get your services noticed by `plone.server`.

In your application `__init__.py` file, you can simply provide a `scan` call.

```python
from plone.server import configure

def includeme(root):
    configure.scan('my.package.addon')
```


## Layers

Your addon can also install layers for your application to lookup views and adapters
from:

```python

from plone.server.addons import Addon
from plone.server.registry import ILayers

LAYER = 'pserver.myaddon.interfaces.ILayer'

@configure.addon(
    name="myaddon",
    title="My addon")
class MyAddon(Addon):

    @classmethod
    def install(self, request):
      registry = request.site_settings
      registry.for_interface(ILayers).active_layers |= {
          LAYER
      }

    @classmethod
    def uninstall(self, request):
      registry = request.site_settings
      registry.for_interface(ILayers).active_layers -= {
        LAYER
      }
```

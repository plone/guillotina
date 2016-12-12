# ADDONS

Addons are integrations that can be installed or uninstalled against a Plone site.
`plone.server` applications can provide potentially many addons. If you have
not read the section on applications, please read that before you come here. The
only way to provide addons is to first implement a `plone.server` application.


## CREATING AN ADDON

Create an addon installer class in an `install.py` file in your `plone.server` application:

```python

from plone.server.addons import Addon
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

Then, in your `configure.zcml` file, register the addon::

```xml
<configure xmlns="http://namespaces.zope.org/zope"
         xmlns:plone="http://namespaces.plone.org/plone">

<include package="plone.server" file="meta.zcml" />
<plone:addon
    name="myaddon"
    title="My addon"
    handler="pserver.myaddon.install.MyAddon" />

</configure>
```


## LAYERS

Your addon can also install layers for your application to lookup views and adapters
from:

```python

from plone.server.addons import Addon
from plone.server.registry import ILayers
LAYER = 'pserver.myaddon.interfaces.ILayer'
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

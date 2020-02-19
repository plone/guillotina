======
Addons
======

Addons are integrations that can be installed or uninstalled against a Guillotina container.
Guillotina applications can potentially provide many addons.
If you have not read the section on :doc:`applications <applications>`, please read that before you come here.

The only way to provide add-ons is to first implement a Guillotina application.


Creating an Addon
=================

Create an addon installer class in an `install.py` file in your Guillotina application:

.. code-block:: python

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


.. include:: ./_scanning.rst


Layers
======

A Layer is a marker you install with your addon, this allows your application 
to lookup views and adapters (override core functionality) only for the container
you installed the add-on. 


.. code-block:: python

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
           registry = task_vars.registry.get()
           registry.for_interface(ILayers).active_layers |= {
               LAYER
           }

       @classmethod
       def uninstall(cls, container, request):
           registry = task_vars.registry.get()
           registry.for_interface(ILayers).active_layers -= {
               LAYER
           }


Installing an Addon into a container
====================================

Addons can be installed into a container using ``@addons`` endpoint by providing
addon name as `id` For example:


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


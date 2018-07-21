Container
=========


.. ignored http call below to make sure we have a container

.. http:gapi::
   :path: /db
   :path_spec: /(db)
   :method: POST
   :basic_auth: root:root
   :headers: Content-Type: application/json
   :body: {"@type": "Container", "id": "container"}
   :hidden:

.. http:gapi::
   :path_spec: /(db)/(container)
   :path: /db/container
   :basic_auth: root:root


Types
-----

.. http:gapi::
   :path_spec: /(db)/(container)/@types
   :path: /db/container/@types
   :basic_auth: root:root


.. http:gapi::
   :path_spec: /(db)/(container)/@types/(type_name)
   :path: /db/container/@types/Item
   :basic_auth: root:root



User
----

.. http:gapi::
   :path_spec: /(db)/(container)/@user
   :path: /db/container/@user
   :basic_auth: root:root


Registry
--------


.. http:gapi::
   :path_spec: /(db)/(container)/@registry
   :path: /db/container/@registry
   :basic_auth: root:root


.. http:gapi::
   :path_spec: /(db)/(container)/@registry
   :method: POST
   :path: /db/container/@registry
   :basic_auth: root:root
   :body: {"interface": "guillotina.documentation.IRegistryData"}


.. http:gapi::
   :path_spec: /(db)/(container)/@registry/(key)
   :method: PATCH
   :path: /db/container/@registry/guillotina.documentation.IRegistryData.foobar
   :basic_auth: root:root
   :body: {"value": "something"}


.. http:gapi::
   :path_spec: /(db)/(container)/@registry/(key)
   :path: /db/container/@registry/guillotina.documentation.IRegistryData.foobar
   :basic_auth: root:root



Addons
------

.. http:gapi::
   :path_spec: /(db)/(container)/@addons
   :path: /db/container/@addons
   :basic_auth: root:root


.. http:gapi::
   :path_spec: /(db)/(container)/@addons
   :path: /db/container/@addons
   :method: POST
   :basic_auth: root:root
   :body: {"id": "docaddon"}


.. http:gapi::
   :path_spec: /(db)/(container)/@addons
   :path: /db/container/@addons
   :method: DELETE
   :basic_auth: root:root
   :body: {"id": "docaddon"}


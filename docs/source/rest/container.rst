Container
=========


.. ignored http call below to make sure we have a container
.. http:gapi::
   :hidden:
   :path: /db
   :path_spec: /(db)
   :method: POST
   :basic_auth: root:root
   :headers: Content-Type: application/json
   :body: {"@type": "Container", "id": "container"}

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



Dynamic Fields
--------------

Dynamic fields are done with the `IDynamicFields` behavior so
first we add the behavior.

.. http:gapi::
   :path_spec: /(db)/(container)/@behaviors
   :path: /db/container/@behaviors
   :method: PATCH
   :basic_auth: root:root
   :body: {"behavior": "guillotina.behaviors.dynamic.IDynamicFields"}


Then, we can add a field.

.. http:gapi::
   :path_spec: /(db)/(container)
   :path: /db/container
   :method: PATCH
   :basic_auth: root:root
   :body: {
      "guillotina.behaviors.dynamic.IDynamicFields": {
         "fields": {
            "foobar": {
               "title": "Hello field",
               "type": "text"
            }
         }
      }}


To inspect the dynamic fields available on content

.. http:gapi::
   :path_spec: /(db)/(container)/@dynamic-fields
   :path: /db/container/@dynamic-fields
   :method: GET
   :basic_auth: root:root



Update dynamic field values

.. http:gapi::
   :path_spec: /(db)/(container)/(id)
   :path: /db/container
   :method: POST
   :basic_auth: root:root
   :body: {
      "@type": "Item",
      "id": "foobar-fields",
      "@behaviors": ["guillotina.behaviors.dynamic.IDynamicFieldValues"]}


.. http:gapi::
   :path_spec: /(db)/(container)/(id)
   :path: /db/container/foobar-fields
   :method: PATCH
   :basic_auth: root:root
   :body: {
         "guillotina.behaviors.dynamic.IDynamicFieldValues": {
            "values": {
               "op": "update",
               "value": [{
                  "key": "foobar",
                  "value": "value"
               }]
            }
         }
      }


.. http:gapi::
   :path_spec: /(db)/(container)/(id)
   :path: /db/container/foobar-fields?include=guillotina.behaviors.dynamic.IDynamicFieldValues
   :method: GET
   :basic_auth: root:root


Search
------

(Requires `guillotina.contrib.catalog.pg` application activated with PostgreSQL)

The `@search` endpoint accepts both `POST` and `GET` requests. The default search
parser and query syntax is flat and does not support nested queries.

`POST` works with a json body while `GET` works on query params.

Supported params:

- `[term]`: Generic search term support. See modifier list below for usage.
- `_from`: start from a point in search results
- `_size`: How large of result set. Max of 50.
- `_sort_asc`: How ascending field
- `_sort_des`: How descending field
- `_metadata`: list of metadata fields to include
- `_metadata_not`: list of metadata fields to exclude

- `__eq`: also the default functionality
- `__not`
- `__gt`
- `__gte`
- `__lte`
- `__lt`
- `__in`


.. http:gapi::
   :path_spec: /(db)/(container)/@search
   :path: /db/container/@search
   :method: POST
   :basic_auth: root:root
   :body: {
         "type_name": "Item",
         "_from": 10,
         "_size": 5,
         "modification_date__gt": "2019-06-15T18:37:31.008359+00:00",
         "_sort_asc": "modification_date",
         "_metadata": "title,description"
      }

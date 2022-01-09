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


Metadata
--------

.. http:gapi::
   :path_spec: /(db)/(container)/@metadata
   :path: /db/container/@metadata
   :basic_auth: root:root

Example:

.. code-block:: json

   {
      "@id": "http://localhost:8070/db/container",
      "types": {
         "Item": {
               "uuid": "keyword",
               "type_name": "keyword",
               "title": "text",
               "modification_date": "date",
               "creation_date": "date",
               "access_roles": "keyword",
               "id": "keyword",
               "access_users": "keyword",
               "path": "path",
               "depth": "int",
               "parent_uuid": "keyword",
               "tid": "keyword"
         },
         "Folder": {
               "uuid": "keyword",
               "type_name": "keyword",
               "title": "text",
               "modification_date": "date",
               "creation_date": "date",
               "access_roles": "keyword",
               "id": "keyword",
               "access_users": "keyword",
               "path": "path",
               "depth": "int",
               "parent_uuid": "keyword",
               "tid": "keyword"
         },
         "Container": {
               "uuid": "keyword",
               "type_name": "keyword",
               "title": "text",
               "modification_date": "date",
               "creation_date": "date",
               "access_roles": "keyword",
               "id": "keyword",
               "access_users": "keyword",
               "path": "path",
               "depth": "int",
               "parent_uuid": "keyword",
               "tid": "keyword"
         },
         "Customer": {
               "uuid": "keyword",
               "type_name": "keyword",
               "title": "text",
               "modification_date": "date",
               "creation_date": "date",
               "access_roles": "keyword",
               "id": "keyword",
               "access_users": "keyword",
               "path": "path",
               "depth": "int",
               "parent_uuid": "keyword",
               "tid": "keyword",
               "archived": "boolean",
               "ratehourly": "int"
         },
         "User": {
               "uuid": "keyword",
               "type_name": "keyword",
               "title": "text",
               "modification_date": "date",
               "creation_date": "date",
               "access_roles": "keyword",
               "id": "keyword",
               "access_users": "keyword",
               "path": "path",
               "depth": "int",
               "parent_uuid": "keyword",
               "tid": "keyword",
               "email": "keyword",
               "name": "textkeyword",
               "user_roles": "textkeyword",
               "disabled": "boolean"
         },
         "UserManager": {
               "uuid": "keyword",
               "type_name": "keyword",
               "title": "text",
               "modification_date": "date",
               "creation_date": "date",
               "access_roles": "keyword",
               "id": "keyword",
               "access_users": "keyword",
               "path": "path",
               "depth": "int",
               "parent_uuid": "keyword",
               "tid": "keyword"
         },
         "Group": {
               "uuid": "keyword",
               "type_name": "keyword",
               "title": "text",
               "modification_date": "date",
               "creation_date": "date",
               "access_roles": "keyword",
               "id": "keyword",
               "access_users": "keyword",
               "path": "path",
               "depth": "int",
               "parent_uuid": "keyword",
               "tid": "keyword",
               "name": "textkeyword",
               "user_roles": "textkeyword",
               "users": "textkeyword"
         },
         "GroupManager": {
               "uuid": "keyword",
               "type_name": "keyword",
               "title": "text",
               "modification_date": "date",
               "creation_date": "date",
               "access_roles": "keyword",
               "id": "keyword",
               "access_users": "keyword",
               "path": "path",
               "depth": "int",
               "parent_uuid": "keyword",
               "tid": "keyword"
         }
      },
      "behaviors": {
         "guillotina.behaviors.attachment.IAttachment": {},
         "guillotina.behaviors.attachment.IMultiAttachment": {},
         "guillotina.behaviors.dublincore.IDublinCore": {
               "creators": "keyword",
               "tags": "keyword",
               "contributors": "keyword"
         },
         "guillotina.behaviors.dynamic.IDynamicFields": {},
         "guillotina.behaviors.dynamic.IDynamicFieldValues": {}
      }
   }


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

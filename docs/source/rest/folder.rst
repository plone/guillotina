Folder
======

.. ignored http call below to make sure we have a container
.. http:gapi::
   :hidden:
   :path: /db
   :method: POST
   :basic_auth: root:root
   :headers: Content-Type: application/json
   :body: {"@type": "Container", "id": "container"}

.. http:gapi::
   :path_spec: /(db)/(container)
   :method: POST
   :path: /db/container
   :basic_auth: root:root
   :headers: Content-Type:application/json
   :body: {"@type": "Folder", "id": "foobar"}


.. http:gapi::
   :path_spec: /(db)/(container)/(id)
   :path: /db/container/foobar
   :method: PATCH
   :basic_auth: root:root
   :headers: Content-Type:application/json
   :body: {"title": "foobar"}


.. http:gapi::
   :path_spec: /(db)/(container)/(id)
   :path: /db/container/foobar
   :basic_auth: root:root


.. http:gapi::
   :path_spec: /(db)/(container)/(id)
   :path: /db/container/foobar
   :method: DELETE
   :basic_auth: root:root


Behaviors
---------

.. http:gapi::
   :path_spec:  /(db)/(container)
   :method: POST
   :path: /db/container
   :basic_auth: root:root
   :headers: Content-Type:application/json
   :body: {"@type": "Folder", "id": "foobar"}
   :hidden: yes

.. http:gapi::
   :path_spec: /(db)/(container)/(id)/@behaviors
   :path: /db/container/foobar/@behaviors
   :basic_auth: root:root

.. http:gapi::
   :path_spec: /(db)/(container)/(id)/@behaviors
   :path: /db/container/foobar/@behaviors
   :method: PATCH
   :basic_auth: root:root
   :headers: Content-Type:application/json
   :body: {"behavior": "guillotina.behaviors.attachment.IAttachment"}

.. http:gapi::
   :path_spec: /(db)/(container)/(id)/@behaviors
   :path: /db/container/foobar/@behaviors
   :method: DELETE
   :basic_auth: root:root
   :headers: Content-Type:application/json
   :body: {"behavior": "guillotina.behaviors.attachment.IAttachment"}


Files
-----

.. http:gapi::
   :path_spec: /(db)/(container)/(id)/@behaviors
   :path: /db/container/foobar/@behaviors
   :method: PATCH
   :basic_auth: root:root
   :headers: Content-Type:application/json
   :body: {"behavior": "guillotina.behaviors.attachment.IAttachment"}
   :hidden: yes


.. http:gapi::
   :path_spec: /(db)/(container)/(id)/@upload/(field_name)
   :path: /db/container/foobar/@upload/file
   :method: PATCH
   :basic_auth: root:root
   :body: foobar data


.. http:gapi::
   :path_spec: /(db)/(container)/(id)/@download/(field_name)
   :path: /db/container/foobar/@download/file
   :basic_auth: root:root


Security
--------

.. http:gapi::
   :path_spec: /(db)/(container)/(id)/@all_permissions
   :path: /db/container/foobar/@all_permissions
   :basic_auth: root:root


.. http:gapi::
   :path_spec: /(db)/(container)/(id)/@canido
   :path: /db/container/foobar/@canido?permissions=guillotina.ModifyContent,guillotina.AccessContent
   :basic_auth: root:root


.. http:gapi::
   :path_spec: /(db)/(container)/(id)/@sharing
   :path: /db/container/foobar/@sharing
   :basic_auth: root:root


.. http:gapi::
   :path_spec: /(db)/(container)/(id)/@sharing
   :path: /db/container/foobar/@sharing
   :method: POST
   :basic_auth: root:root
   :headers: Content-Type:application/json
   :body: {
        "prinrole": [{
            "principal": "foobar",
            "role": "guillotina.Owner",
            "setting": "Allow"
        }]}

.. http:gapi::
   :path_spec: /(db)/(container)/(id)/@sharing
   :path: /db/container/foobar/@sharing
   :method: PUT
   :basic_auth: root:root
   :headers: Content-Type:application/json
   :body: {
        "prinrole": [{
            "principal": "foobar",
            "role": "guillotina.Owner",
            "setting": "Allow"
        }]}


Content
-------

.. http:gapi::
   :path_spec: /(db)/(container)/(id)/@move
   :path: /db/container/foobar/@move
   :method: POST
   :basic_auth: root:root
   :headers: Content-Type:application/json
   :body: {
        "destination": "",
        "new_id": "foobar2"
        }


.. http:gapi::
   :path_spec: /(db)/(container)/(id)/@duplicate
   :path: /db/container/foobar2/@duplicate
   :method: POST
   :basic_auth: root:root
   :headers: Content-Type:application/json
   :body: {
        "destination": "",
        "new_id": "foobar3"
        }


.. http:gapi::
   :path_spec: /(db)/(container)/(id)/@addable-types
   :path: /db/container/foobar3/@addable-types
   :basic_auth: root:root


.. http:gapi::
   :path_spec: /(db)/(container)/(id)/@ids
   :path: /db/container/foobar3/@ids
   :basic_auth: root:root


.. http:gapi::
   :path_spec: /(db)/(container)/(id)/@items
   :path: /db/container/foobar3/@items
   :basic_auth: root:root


.. http:gapi::
   :path_spec: /(db)/(container)/(id)/@invalidate-cache
   :path: /db/container/foobar3/@invalidate-cache
   :basic_auth: root:root

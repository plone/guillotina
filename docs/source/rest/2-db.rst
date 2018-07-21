Database
========

.. ignored http call below to make sure we don't have a container already
.. http:gapi::
   :hidden:
   :path_spec: /(db)/(container)
   :path: /db/container
   :method: DELETE
   :basic_auth: root:root

.. http:gapi::
   :path: /db
   :path_spec: /(db)
   :method: POST
   :basic_auth: root:root
   :headers: Content-Type: application/json
   :body: {"@type": "Container", "id": "container"}


.. http:gapi::
   :path_spec: /(db)
   :path: /db
   :basic_auth: root:root
Search
======


Search
------

.. note:: Requires `guillotina.contrib.catalog.pg` application activated with PostgreSQL.

The `@search` endpoint accepts `GET` requests.
It is available for container and resources.
The default search parser and query syntax is flat and does not support nested queries.


.. http:gapi::
   :path_spec: /(db)/(container)/@search
   :path: /db/container/@search
   :basic_auth: root:root


.. http:gapi::
   :path_spec: /(db)/(container)/(id)/@search
   :path: /db/container/foobar/@search
   :basic_auth: root:root


.. warning:: The POST request to `@search` endpoint is not implemented.

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


Use cases
^^^^^^^^^

  - Search for specific sentence on text field
  - Search for words on text field
  - Search for not having a value on a field
  - Search for wildcard on text field
  - Search for keyword on filter
  - Search for number and comparisons on numeric field
  - Search for paths

  - Define from which element you want to search
  - Define the search size return
  - Define metadata included and excluded on the result
  - Return full objects

Implementation details
^^^^^^^^^^^^^^^^^^^^^^

A list::

  query : term=first+second+third
  result : term = first, second, third

Text field search specific text/sentence::

  query : title__eq=my+sentence

Text field search words text::

  query : title__in=my+sentence

Text field search not words text::

  query : title__not=not+willing+words

Text field search wildcard text::

  query : title__wildcard=will*

Keyword on filter::

  query : subject=guillotina

Number on field::

  query : age=39
  query : age__gte=39
  query : age__lte=39

Date on field::

  query : creation=10-09-2018
  query : creation__gte=10-09-2018
  query : creation__lte=10-09-2018

Which metadata to return::

  query : _metadata=title+description
  query : _metadata_not=language+description

Sort::

  query : _sort_asc=age

Search size::

  query : _size=30

From which element to return::

  query : _from=30

Search for paths::

  query : path__starts=plone+folder
  result : elements on /plone/folder

Escape +::

  query : term=hola++adeu
  result : term=hola+adeu

Return full object::

  query : _fullobject=true


Examples
^^^^^^^^^

Plone call::

  GET /plone/@search?path.query=%2Ffolder&path.depth=2

Guillotina call::

  GET @search?path_starts=folder&depth_gte=2

Plone call::

  GET /plone/@search?Title=lorem&portal_type=Document

Guillotina call::
  
  GET @search?title_in=lorem&portal_type=Document


Aggregation
-----------

.. http:gapi::
   :path_spec: /(db)/(container)/(id)/@aggregation
   :path: /db/container/foobar/@aggregation
   :basic_auth: root:root

Example:

.. code-block:: http

  @aggregation?title__eq=my+title&metadata=title,creators


.. code-block:: json

  {
    "title": {
      "items": {
        "Item2": 1
      },
      "total": 1
    },
    "creators": {
      "items": {
        "root": 1
      },
      "total": 1
    }
  }

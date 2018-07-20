The Python AsyncIO REST API Framework
=====================================

(REST Resource Application Server)

Guillotina is the only full-featured Python AsyncIO REST Resource Application
Server designed for high-performance, horizontally scaling solutions.

Guillotina is powerful datastore, capable of storing and indexing milions of objects.

It is a high performance web server based on many of the technologies and lessons learned
from Plone, Pyramid, Django and others all while utilizing Python's great AsyncIO library.

Using Python's AsyncIO, it works well with micro-service oriented environments.

Features:
 - REST JSON API
 - Built-in authentication/authorization, built-in JWT support
 - Hierarchical data/url structure. Object storage.
 - Permissions/roles/groups
 - Fully customizable permission/roles/groups based on hierarchical data structure
 - Robust customizable component architecture and configuration syntax
 - Content types, dynamic behaviors, based on python interfaces and json schemas.
 - Built-in CORS support
 - Serialitzation/Validiation library integrated.
 - Elastic search integration throught guillotina_elasticsearch, or fallback to postgres
   json indexing.
 - Declarative configuration using decorators.
 - Integrated cloud storage file uploads.
 - py.test fixtues for easy service/api/endpoint testing
 - Built-in command system to run jobs.
 - Rich ecosystem of additional packages for adding additional features: Integration with
   rabbitmq, batching of queries, redis cache layer.
 - Powerful  addon architecture based on Zope Component Architecture.






Detailed Documentation
======================

 .. toctree::
    :maxdepth: 2

    about
    quickstart
    rest/indext
    installation/index
    awesome
    developer/index
    training/index


What is Guillotina like?
========================

Example configuration:

.. literalinclude:: examples/config.yaml

Example service:

.. literalinclude:: examples/service.py

Example content type:

.. literalinclude:: examples/ct.py

Example usage:

.. http:post:: /db/container

     Create MyType

     **Example request**

     .. sourcecode:: http

        POST /db/container HTTP/1.1
        Accept: application/json
        Content-Type: application/json
        Authorization: Basic cm9vdDpyb290

        {
          "@type": "MyType",
          "id": "foobar",
          "foobar": "foobar"
        }

     **Example response**

     .. sourcecode:: http

        HTTP/1.1 201 OK
        Content-Type: application/json

     :reqheader Authorization: Required token to authenticate
     :statuscode 201: no error
     :statuscode 401: Invalid Auth code
     :statuscode 500: Error processing request


.. http:get:: /db/container/foobar/@foobar

    Get MyType

    **Example request**

    .. sourcecode:: http

       GET /db/container/foobar HTTP/1.1
       Accept: application/json
       Authorization: Basic cm9vdDpyb290

    **Example response**

    .. sourcecode:: http

       HTTP/1.1 201 OK
       Content-Type: application/json

       {"foo": "bar"}

    :reqheader Authorization: Required token to authenticate
    :statuscode 200: no error
    :statuscode 401: Invalid Auth code
    :statuscode 500: Error processing request

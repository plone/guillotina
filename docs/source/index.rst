.. raw:: html

    <h1>The Python AsyncIO REST API Framework</h1>


Guillotina is the only full-featured Python AsyncIO REST Resource Application
Server designed for high-performance, horizontally scaling solutions.

.. toctree::
   :caption: About
   :hidden:
   :maxdepth: 1

   about

========
Features
========

 - **Performance**: Traditional Python web servers limit the number of simultaneous
   requests to the number of threads running the server. With AsyncIO, you are
   able to serve many more simultaneous requests.
 - **Front-end friendly**: Guillotina is designed to make your
   JavaScript engineers happy. With things like automatic Swagger documentation
   for endpoints, out of the box CORS and websockets, your front-end team will be happy
   to work with Guillotina. We speak JSON but can adapt to any content type
   payload request/response bodies.
 - **AsyncIO**: With AsyncIO, websockets are simple. More interestingly, AsyncIO
   is an ideal match with microservice architectures.
 - **Object model**: Guillotina uses a hierarchial object model. This hierarchy
   of objects then maps to URLs and is perfect for managing
   a large number of objects.
 - **Security**: Guillotina has a granular, hierarchical, multidimensional
   security system that allows you to manage the security of your content
   at a level not available to other frameworks.
 - **Scale**: With integrations like Redis, ElasticSearch and Cockroach, you
   have the tools to scale.


.. toctree::
   :caption: Getting Started
   :hidden:
   :maxdepth: 1

   quick-start
   quick-tour

=====================
Understand The Basics
=====================

Are you new to Guillotina?

The :doc:`quick-tour` gives an overview of the major features in Guillotina.

Need help? Join our `Gitter channel <https://gitter.im/plone/guillotina>`_.




.. toctree::
   :caption: Tutorial
   :hidden:
   :maxdepth: 1

   training/index
   training/install
   training/running
   training/configuration
   training/api
   training/asyncio
   training/commands


.. toctree::
   :caption: Develop
   :hidden:
   :maxdepth: 1

   developer/index


.. toctree::
   :caption: OpenAPI
   :hidden:
   :maxdepth: 1

   api/index


.. toctree::
   :caption: Deploy
   :hidden:
   :maxdepth: 1

   deploying






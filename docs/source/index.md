# Guillotina: The Python AsyncIO REST API Framework

Guillotina is the only full-featured Python AsyncIO REST Resource Application
Server designed for high-performance, horizontally scaling solutions.

## Quick Start

Install Guillotina:

```shell
pip install guillotina
g serve --port=8080
```

Then use curl, [Postman](https://www.postman.com/ "Link to Postman") or build something with it:

```shell
curl -XPOST --user root:root http://localhost:8080/db -d '{
  "@type": "Container",
  "id": "container"
}'
curl --user root:root http://localhost:8080/db/container
```

## Why Guillotina

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

## Getting started

Are you new to Guillotina? This is the place to start!

The {doc}`quick tour <quick-tour>` gives an overview of the major features in Guillotina.

Need help? Join our [Gitter channel](https://gitter.im/plone/guillotina).

## Build a Guillotina app

You can even run Guillotina as a single page app if you so desire.

Here is an example with content type and service::

```python
from guillotina import configure
from guillotina import content
from guillotina import schema
from guillotina.factory import make_app
from zope import interface

import uvicorn


class IMyType(interface.Interface):
    foobar = schema.TextLine()


@configure.contenttype(
    type_name="MyType",
    schema=IMyType,
    behaviors=["guillotina.behaviors.dublincore.IDublinCore"],
)
class MyType(content.Resource):
    pass


@configure.service(
    context=IMyType,
    method="GET",
    permission="guillotina.ViewContent",
    name="@foobar",
)
async def foobar_service(context, request):
    return {"foobar": context.foobar}


if __name__ == "__main__":
    app = make_app(
        settings={
            "applications": ["__main__"],
            "root_user": {"password": "root"},
            "databases": {
                "db": {"storage": "DUMMY_FILE", "filename": "dummy_file.db",}
            },
            "port": 8080,
        }
    )
    uvicorn.run(app, host="localhost", port=8080)
```


## Getting Started (Tutorials)

Use this section when you are new to Guillotina and want a guided path.

```{eval-rst}
.. toctree::
   :maxdepth: 2

   quickstart
   quick-tour
   training/index
```

## How-To Guides

Use this section for task-oriented guides while building and maintaining your app.

```{eval-rst}
.. toctree::
   :maxdepth: 2

   how-to/index
```

## Concepts

Use this section to understand architecture, security model, and core design choices.

```{eval-rst}
.. toctree::
   :maxdepth: 2

   concepts/index
```

## Developer Guides

Use this section when extending Guillotina internals, components, and services.

```{eval-rst}
.. toctree::
   :maxdepth: 2

   developer/index
```

## Reference

Use this section for API-level lookups and endpoint behavior.

```{eval-rst}
.. toctree::
   :maxdepth: 2

   rest/index
   api/index
```

## Operations

Use this section for deployment, configuration, and upgrade guidance.

```{eval-rst}
.. toctree::
   :maxdepth: 2

   operations/index
```

## Contrib Packages

```{eval-rst}
.. toctree::
   :maxdepth: 2

   contrib/index
```

## About

- {doc}`Read about <about>` the rich history of the project

```{eval-rst}
.. toctree::
   :hidden:
   :glob:

   about
   quick-tour
   quickstart
   concepts/index
   how-to/index
   operations/index
   rest/index
   developer/*
   installation/*
   training/*
   training/extending/*
```

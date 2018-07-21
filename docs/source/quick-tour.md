# Quick tour of Guillotina

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


What is Guillotina like?
========================

### Example configuration:

```eval_rst
.. literalinclude:: examples/quick-tour/config.yaml
```

### Example service:

See [instructions below](#playing-with-those-examples) to play with.

```eval_rst
.. literalinclude:: examples/quick-tour/service.py
```

### Example content type:

See [instructions below](#playing-with-those-examples) to play with.

```eval_rst
.. literalinclude:: examples/quick-tour/ct.py
```

### Example usage:

See [instructions below](#playing-with-those-examples) to play with.

```eval_rst
.. http:post:: /db/container/

    Create MyType

    **Example**

    ..  http:example:: curl wget httpie python-requests

        POST /db/container HTTP/1.1
        Accept: application/json
        Content-Type: application/json
        Host: localhost:8080
        Authorization: Basic cm9vdDpyb290

        {
          "@type": "MyType",
          "id": "foobar",
          "foobar": "foobar"
        }


        HTTP/1.1 201 OK
        Content-Type: application/json

    :reqheader Authorization: Required token to authenticate
    :statuscode 201: no error
    :statuscode 401: Invalid Auth code
    :statuscode 500: Error processing request


.. http:get:: /db/container/foobar/

    Get MyType

    **Example**

    ..  http:example:: curl wget httpie python-requests

        GET /db/container/foobar HTTP/1.1
        Accept: application/json
        Host: localhost:8080
        Authorization: Basic cm9vdDpyb290


        HTTP/1.1 200 OK
        Content-Length: 851
        Content-Type: application/json

        {
            "@id": "http://localhost:8080/db/container/foobar",
            "@name": "foobar",
            "@type": "MyType",
            "@uid": "e3f|81c5406638bd4a68b89275f739fc18b2",
            "UID": "e3f|81c5406638bd4a68b89275f739fc18b2",
            "creation_date": "2018-07-21T13:14:15.245181+00:00",
            "foobar": "foobar",
            "guillotina.behaviors.dublincore.IDublinCore": {
                "contributors": [
                    "root"
                ],
                "creation_date": "2018-07-21T13:14:15.245181+00:00",
                "creators": [
                    "root"
                ],
                "description": null,
                "effective_date": null,
                "expiration_date": null,
                "modification_date": "2018-07-21T13:14:15.245181+00:00",
                "publisher": null,
                "tags": null,
                "title": null
            },
            "is_folderish": false,
            "modification_date": "2018-07-21T13:14:15.245181+00:00",
            "parent": {
                "@id": "http://localhost:8080/db/container",
                "@name": "container",
                "@type": "Container",
                "@uid": "e3f4e401d12843a4a303666da4158458",
                "UID": "e3f4e401d12843a4a303666da4158458"
            }
        }



    :reqheader Authorization: Required token to authenticate
    :statuscode 200: no error
    :statuscode 401: Invalid Auth code
    :statuscode 500: Error processing request


.. http:post:: /db/@foobar

    Use foobar service

    **Example**

    ..  http:example:: curl wget httpie python-requests

        POST /db/@foobar HTTP/1.1
        Accept: application/json
        Host: localhost:8080
        Authorization: Basic cm9vdDpyb290


        HTTP/1.1 201 OK
        Content-Type: application/json

        { "foo": "bar"}

    or

    ..  http:example:: curl wget httpie python-requests

        POST /db/container/@foobar HTTP/1.1
        Accept: application/json
        Host: localhost:8080
        Authorization: Basic cm9vdDpyb290


        HTTP/1.1 201 OK
        Content-Type: application/json

        { "foo": "bar"}

    or

    ..  http:example:: curl wget httpie python-requests

        POST /db/container/foobar/@foobar HTTP/1.1
        Accept: application/json
        Host: localhost:8080
        Authorization: Basic cm9vdDpyb290


        HTTP/1.1 201 OK
        Content-Type: application/json

        { "foo": "bar"}


    :reqheader Authorization: Required token to authenticate
    :statuscode 200: no error
    :statuscode 401: Invalid Auth code
    :statuscode 500: Error processing request

    You can see that `@foobar` service is available on any endpoints.
```

### Playing with those examples

In order to play with those examples you should install guillotina and cookiecutter, let's do that in a python virtualenv:

```
$ virtualenv .
$ source ./bin/activate
$ pip install guillotina cookiecutter
```

Then use guillotina templates to create an application:

```
$ ./bin/g create --template=application
Could not find the configuration file config.json. Using default settings.
full_name []: My App
email []: guillotina@myapp.io
package_name [guillotina_myproject]: myapp
project_short_description [Guillotina server application python project]:
Select open_source_license:
1 - MIT license
2 - BSD license
3 - ISC license
4 - Apache Software License 2.0
5 - GNU General Public License v3
6 - Not open source
Choose from 1, 2, 3, 4, 5, 6 [1]:
```

You should now have a structure like the following one:

```
.
└── myapp
    ├── README.rst
    ├── config.yaml
    ├── myapp
    │   ├── __init__.py
    │   ├── api.py
    │   └── install.py
    └── setup.py
```

Now copy [Example content type](#example-content-type) section content in `myapp/myapp/content.py`.

Add `configure.scan('myapp.content')` to `myapp/myapp/__init__.py` `includeme` function.

`@foobar` service is already defined in `myapp/mayapp/api.py`.

Then install `myapp`:

```
$ pip install -e myapp
```

Edit `myapp/config.yaml` to fit your needs, especially in term of db configuration.

And run guillotina with:

```
$ g serve -c myapp/config.yaml
```

Now create a container:


```eval_rst
..  http:example:: curl wget httpie python-requests

    POST /db/ HTTP/1.1
    Accept: application/json
    Content-Type: application/json
    Host: localhost:8080
    Authorization: Basic cm9vdDpyb290

    {
        "@type": "Container",
        "title": "Container 1",
        "id": "container",
        "description": "Description"
    }


    HTTP/1.1 201 OK
    Content-Type: application/json

```

You can now use all above examples.

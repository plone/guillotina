# Quickstart

How to quickly get started using `guillotina`.

This tutorial will assume usage of virtualenv. You can use your own preferred
tool for managing your python environment.

*This tutorial assumes you have postgresql running*

Setup the environment:

```
virtualenv .
```

Install `guillotina`:

```
./bin/pip install guillotina
```

Generate configuration file (requires `cookiecutter`):

```
./bin/pip install cookiecutter
./bin/g create --template=configuration
```

Finally, run the server:

```
./bin/g
```

The server should now be running on http://0.0.0.0:8080

Then, [use Postman](https://www.getpostman.com/), `curl` or whatever tool you
prefer to interact with the [REST API](./rest/index.html).

You can also navigate in your Guillotina server with its built-in web admin interface by visiting http://localhost:8080/+admin/.

Modify the configuration in `config.yaml` to customize server setttings.


### Postgresql installation instructions

If you do not have a postgresql database server installed, you can use docker
to get one running quickly.

Example docker run command:

```
docker run -e POSTGRES_DB=guillotina -e POSTGRES_USER=guillotina -p 127.0.0.1:5432:5432 postgres:9.6
```


## Creating a container

Guillotina containers are the building block of all other content. A container
is where you place all other content for your application. Only containers can
be created inside databases.

Let's create one:

```eval_rst
..  http:example:: curl wget httpie python-requests

    POST /db/ HTTP/1.1
    Accept: application/json
    Content-Type: application/json
    Host: localhost:8080
    Authorization: Basic cm9vdDpyb290

    {
        "@type": "Container",
        "title": "Guillotina 1",
        "id": "guillotina",
        "description": "Description"
    }


    HTTP/1.1 201 OK
    Content-Type: application/json

```

and create content inside the container:

```eval_rst
..  http:example:: curl wget httpie python-requests

    POST /db/guillotina/ HTTP/1.1
    Accept: application/json
    Content-Type: application/json
    Host: localhost:8080
    Authorization: Basic cm9vdDpyb290

    {
        "@type": "Item",
        "title": "News",
        "id": "news"
    }


    HTTP/1.1 201 OK
    Content-Type: application/json

```

## Retrieving your data

Let's navigating throught your newly created data.

First you can see all your containers using the following, notice that at the moment there's only one named `guillotina`:

```eval_rst
..  http:example:: curl wget httpie python-requests

    GET /db/ HTTP/1.1
    Accept: application/json
    Host: localhost:8080
    Authorization: Basic cm9vdDpyb290


    HTTP/1.1 200 OK
    Content-Type: application/json

    {
        "@type": "Database",
        "containers": [
            "guillotina"
        ]
    }

```

Then you could explore container data using:

```eval_rst
..  http:example:: curl wget httpie python-requests

    GET /db/guillotina HTTP/1.1
    Accept: application/json
    Host: localhost:8080
    Authorization: Basic cm9vdDpyb290


    HTTP/1.1 200 OK
    Content-Type: application/json

    {
        "@id": "http://localhost:8080/db/guillotina",
        "@name": "guillotina",
        "@type": "Container",
        "@uid": "7d9ebe1b2e1044688c83985e9e0a7ef3",
        "UID": "7d9ebe1b2e1044688c83985e9e0a7ef3",
        "__behaviors__": [],
        "__name__": "guillotina",
        "creation_date": "2018-07-21T09:37:28.125034+00:00",
        "is_folderish": true,
        "items": [
            {
                "@id": "http://localhost:8080/db/guillotina/news",
                "@name": "news",
                "@type": "Item",
                "@uid": "7d9|11729830722c4e43924df18d21d14bdf",
                "UID": "7d9|11729830722c4e43924df18d21d14bdf"
            }
        ],
        "length": 1,
        "modification_date": "2018-07-21T09:37:28.125034+00:00",
        "parent": {},
        "title": "Guillotina 1",
        "type_name": "Container",
        "uuid": "7d9ebe1b2e1044688c83985e9e0a7ef3"
    }

```

And finally query a specific content inside the container using:

```eval_rst
..  http:example:: curl wget httpie python-requests

    GET /db/guillotina/news HTTP/1.1
    Accept: application/json
    Host: localhost:8080
    Authorization: Basic cm9vdDpyb290


    HTTP/1.1 200 OK
    Content-Type: application/json

    {
        "@id": "http://localhost:8080/db/guillotina/news",
        "@name": "news",
        "@type": "Item",
        "@uid": "7d9|11729830722c4e43924df18d21d14bdf",
        "UID": "7d9|11729830722c4e43924df18d21d14bdf",
        "__behaviors__": [],
        "__name__": "news",
        "creation_date": "2018-07-21T09:37:41.863014+00:00",
        "guillotina.behaviors.dublincore.IDublinCore": {
            "contributors": [
                "root"
            ],
            "creation_date": "2018-07-21T09:37:41.863014+00:00",
            "creators": [
                "root"
            ],
            "description": null,
            "effective_date": null,
            "expiration_date": null,
            "modification_date": "2018-07-21T09:37:41.863014+00:00",
            "publisher": null,
            "tags": null,
            "title": "News"
        },
        "is_folderish": false,
        "modification_date": "2018-07-21T09:37:41.863014+00:00",
        "parent": {
            "@id": "http://localhost:8080/db/guillotina",
            "@name": "guillotina",
            "@type": "Container",
            "@uid": "7d9ebe1b2e1044688c83985e9e0a7ef3",
            "UID": "7d9ebe1b2e1044688c83985e9e0a7ef3"
        },
        "title": "News",
        "type_name": "Item",
        "uuid": "7d9|11729830722c4e43924df18d21d14bdf"
    }

```

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
    :response: ./source/examples/created.response

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

```

and create content inside the container:

```eval_rst
..  http:example:: curl wget httpie python-requests
    :response: ./source/examples/created.response

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

```

## Retrieving your data

Let's navigating throught your newly created data.

First you can see all your containers using the following, notice that at the moment there's only one named `guillotina`:

```eval_rst
..  http:example:: curl wget httpie python-requests
    :response: ./source/examples/quickstart/query_db.response

    GET /db/ HTTP/1.1
    Accept: application/json
    Host: localhost:8080
    Authorization: Basic cm9vdDpyb290

```

Then you could explore container data using:

```eval_rst
..  http:example:: curl wget httpie python-requests
    :response: ./source/examples/quickstart/query_container.response

    GET /db/guillotina HTTP/1.1
    Accept: application/json
    Host: localhost:8080
    Authorization: Basic cm9vdDpyb290

```

And finally query a specific content inside the container using:

```eval_rst
..  http:example:: curl wget httpie python-requests
    :response: ./source/examples/quickstart/query_content.response

    GET /db/guillotina/news HTTP/1.1
    Accept: application/json
    Host: localhost:8080
    Authorization: Basic cm9vdDpyb290

```

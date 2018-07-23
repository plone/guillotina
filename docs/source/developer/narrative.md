# Getting started

In these narrative docs, we'll go through creating a todo application.


## Installation


```
pip install guillotina
```


## Generating the initial application

Guillotina comes with a `cookiecutter` template for creating a base application.

First, install `cookiecutter` if it isn't already installed.

```
pip install cookiecutter
```

Then, run the generate command:

```
guillotina create --template=application
```

Enter `guillotina_todo` for package_name.

Then, install your package:

```
cd guillotina_todo
python setup.py develop
```

## Configuring

The scaffold produces an initial `config.yaml` configuration file for you.

You can inspect and customize your configuration. Most notable is the database
configuration. If you want to run a development `postgresql` server, I
recommend you use docker:

```bash
docker run --rm \
  -e POSTGRES_DB=guillotina \
  -e POSTGRES_USER=guillotina \
  -p 127.0.0.1:5432:5432 \
  --name postgres postgres:9.6
```


## Creating to-do type

Types consist of an interface (schema) using the excellent `zope.interface` package
and a class that uses that interface.

Create a `guillotina_todo/content.py` file with the following:

```python
from guillotina import configure
from guillotina import schema
from guillotina import interfaces
from guillotina import content


class IToDo(interfaces.IItem):
    text = schema.Text()


@configure.contenttype(
    type_name="ToDo",
    schema=IToDo)
class ToDo(content.Item):
    """
    Our ToDo type
    """
```

Then, we want to make sure our content type configuration is getting loaded,
so add this to your `__init__.py` `includeme` function:

```python
from guillotina import configure
configure.scan('guillotina_todo.content')
```

## Running

You run you application by using the guillotina command runner again:

```
guillotina serve -c config.yaml
```


## Creating your todo list

Create container first:

```eval_rst
..  http:example:: curl wget httpie python-requests

    POST /db/ HTTP/1.1
    Accept: application/json
    Authorization: Basic cm9vdDpyb290
    Content-Type: application/json
    Host: localhost:8080

    {
        "@type": "Container",
        "description": "My todo list",
        "id": "todo",
        "title": "ToDo List"
    }


    HTTP/1.1 200 OK
    Content-Type: application/json
    Location: /db/todo

    {
        "@type": "Container",
        "id": "todo",
        "title": "ToDo List"
    }

```

Install your todo list application:

```eval_rst
..  http:example:: curl wget httpie python-requests

    POST /db/todo/@addons HTTP/1.1
    Accept: application/json
    Authorization: Basic cm9vdDpyb290
    Content-Type: application/json
    Host: localhost:8080

    {
        "id": "guillotina_todo"
    }


    HTTP/1.1 200 OK
    Content-Type: application/json

    {
        "available": [
            {
                "id": "guillotina_todo",
                "title": "Guillotina server application python project"
            }
        ],
        "installed": [
            "guillotina_todo"
        ]
    }

```

Add todo items:

```eval_rst
..  http:example:: curl wget httpie python-requests

    POST /db/todo HTTP/1.1
    Accept: application/json
    Authorization: Basic cm9vdDpyb290
    Content-Type: application/json
    Host: localhost:8080

    {
        "@type": "ToDo",
        "text": "Get milk"
    }


    HTTP/1.1 201 Created
    Content-Type: application/json
    Location: http://localhost:8080/db/todo/385ac34a49bc406f8494600c50b99a85

    {
        "@id": "http://localhost:8080/db/todo/385ac34a49bc406f8494600c50b99a85",
        "@name": "385ac34a49bc406f8494600c50b99a85",
        "@type": "ToDo",
        "@uid": "5c9|385ac34a49bc406f8494600c50b99a85",
        "UID": "5c9|385ac34a49bc406f8494600c50b99a85"
    }
```

```eval_rst
..  http:example:: curl wget httpie python-requests

    POST /db/todo HTTP/1.1
    Accept: application/json
    Authorization: Basic cm9vdDpyb290
    Content-Type: application/json
    Host: localhost:8080

    {
        "@type": "ToDo",
        "text": "Do laundry"
    }


    HTTP/1.1 201 Created
    Content-Type: application/json
    Location: http://localhost:8080/db/todo/77332e3153a54924b9b36eb263848826

    {
        "@id": "http://localhost:8080/db/todo/77332e3153a54924b9b36eb263848826",
        "@name": "77332e3153a54924b9b36eb263848826",
        "@type": "ToDo",
        "@uid": "5c9|77332e3153a54924b9b36eb263848826",
        "UID": "5c9|77332e3153a54924b9b36eb263848826"
    }
```

Get a list of todo items:

```eval_rst
..  http:example:: curl wget httpie python-requests

    GET /db/todo HTTP/1.1
    Accept: application/json
    Authorization: Basic cm9vdDpyb290
    Host: localhost:8080


    HTTP/1.1 200 OK
    Content-Type: application/json

    {
        "@id": "http://localhost:8080/db/todo",
        "@name": "todo",
        "@type": "Container",
        "@uid": "5c9932350eaf4ff189d7db934222216b",
        "UID": "5c9932350eaf4ff189d7db934222216b",
        "__behaviors__": [],
        "__name__": "todo",
        "creation_date": "2018-07-21T15:39:11.411162+00:00",
        "is_folderish": true,
        "items": [
            {
                "@id": "http://localhost:8080/db/todo/385ac34a49bc406f8494600c50b99a85",
                "@name": "385ac34a49bc406f8494600c50b99a85",
                "@type": "ToDo",
                "@uid": "5c9|385ac34a49bc406f8494600c50b99a85",
                "UID": "5c9|385ac34a49bc406f8494600c50b99a85"
            },
            {
                "@id": "http://localhost:8080/db/todo/77332e3153a54924b9b36eb263848826",
                "@name": "77332e3153a54924b9b36eb263848826",
                "@type": "ToDo",
                "@uid": "5c9|77332e3153a54924b9b36eb263848826",
                "UID": "5c9|77332e3153a54924b9b36eb263848826"
            }
        ],
        "length": 2,
        "modification_date": "2018-07-21T15:39:11.411162+00:00",
        "parent": {},
        "title": "ToDo List",
        "type_name": "Container",
        "uuid": "5c9932350eaf4ff189d7db934222216b"
    }
```

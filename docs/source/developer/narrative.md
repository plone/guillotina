# Narrative

In these narrative docs, we'll go through creating a todo application.


## Installation


```
pip install guillotina
```


## Generating the initial application

Guillotina comes with a cookie cutter for creating a base application.

First, install cookiecutter if it isn't already installed.

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

The scaffold produces an initial `config.json` configuration file for you.

You can inspect and customize your configuration. Most notably is the database
configuration. If you want to run a development `postgresql` server, the
scaffold ships with a Makefile that provides a command to run a postgresql
docker: `make run-postgres`.


## Creating to do type

Types consist of an interface(schema) using the excellent zope.interface package
and a class that uses that interface.

Create a `content.py` file with the following:

```python
from guillotina import configure
from guillotina import schema
from guillotina.content import Item
from zope.interface import Interface


class IToDo(Interface):
    text = schema.Text()


@configure.contenttype(
    type_name="ToDo",
    schema=IToDo)
class ToDo(Item):
    """
    Our ToDo type
    """
```

Then, we want to make sure out content type configuration is getting loaded,
so add this to your `__init__.py` `includeme` function:

```python
    configure.scan('guillotina_todo.content')
```

## Running

You run you application by using the guillotina command runner again:

```
guillotina serve -c config.json
```


## Creating your todo list

Create container first:

```
curl -X POST -H "Accept: application/json" --user root:root -H "Content-Type: application/json" -d '{
  "@type": "Container",
  "title": "ToDo List",
  "id": "todo",
  "description": "My todo list"
}' "http://127.0.0.1:8080/db/"
```


Install your todo list application:

```
curl -X POST -H "Accept: application/json" --user root:root -H "Content-Type: application/json" -d '{
  "id": "guillotina_todo"
}' "http://127.0.0.1:8080/db/todo/@addons"
```


Add todo items:

```
curl -X POST -H "Accept: application/json" --user root:root -H "Content-Type: application/json" -d '{
  "@type": "ToDo",
  "text": "Get milk"
}' "http://127.0.0.1:8080/db/todo"
```

```
curl -X POST -H "Accept: application/json" --user root:root -H "Content-Type: application/json" -d '{
  "@type": "ToDo",
  "text": "Do laundry"
}' "http://127.0.0.1:8080/db/todo"
```


Get list of todo items:

```
curl -H "Accept: application/json" --user root:root "http://127.0.0.1:8080/db/todo"
```

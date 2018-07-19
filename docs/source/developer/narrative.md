# Narrative

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


## Creating to do type

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

```bash
curl -X POST --user root:root \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
  "@type": "Container",
  "title": "ToDo List",
  "id": "todo",
  "description": "My todo list"
  }' "http://127.0.0.1:8080/db/"
```


Install your todo list application:

```
curl -X POST \
  --user root:root \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
  "id": "guillotina_todo"
  }' "http://127.0.0.1:8080/db/todo/@addons"
```


Add todo items:

```
curl -X POST \
  --user root:root \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
  "@type": "ToDo",
  "text": "Get milk"
  }' "http://127.0.0.1:8080/db/todo"
```

```
curl -X POST \
  --user root:root \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
  "@type": "ToDo",
  "text": "Do laundry"
  }' "http://127.0.0.1:8080/db/todo"
```


Get a list of todo items:

```
curl -H "Accept: application/json" --user root:root "http://127.0.0.1:8080/db/todo"
```

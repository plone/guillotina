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
prefer to interact with the REST API.

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

```
  curl -X POST -H "Accept: application/json" --user root:root -H "Content-Type: application/json" -d '{
    "@type": "Container",
    "title": "Guillotina 1",
    "id": "guillotina",
    "description": "Description"
  }' "http://127.0.0.1:8080/db/"
```

and create content inside the container:

```
  curl -X POST -H "Accept: application/json" --user root:root -H "Content-Type: application/json" -d '{
    "@type": "Item",
    "title": "News",
    "id": "news"
  }' "http://127.0.0.1:8080/db/guillotina/"
```

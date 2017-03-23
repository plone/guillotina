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

Generate configuration file:

```
./bin/guillotina create configuration
```

Finally, run the server:

```
./bin/guillotina
```

The server should now be running on http://0.0.0.0:8080

Then, [use Postman](https://www.getpostman.com/), curl or whatever tool you
prefer to interact with the REST API.

Modify the configuration in config.json to customize server setttings.


### Postgresql installation instructions

If you do not have a postgresql database server installed, you can use docker
to get one running quickly.

Example docker run command:

```
docker run -e POSTGRES_DB=guillotina -e POSTGRES_USER=postgres -p 127.0.0.1:5432:5432 postgres:9.6
```


## Creating default content

Once started, you will require to add at least a Guillotina container to start fiddling around:

```
  curl -X POST -H "Accept: application/json" --user root:root -H "Content-Type: application/json" -d '{
    "@type": "Container",
    "title": "Guillotina 1",
    "id": "guillotina",
    "description": "Description"
  }' "http://127.0.0.1:8080/db/"
```

and give permissions to add content to it:

```
  curl -X POST -H "Accept: application/json" --user root:root -H "Content-Type: application/json" -d '{
    "prinrole": {
        "Anonymous User": ["guillotina.Member", "guillotina.Reader"]
    },
    "type": "Allow"
  }' "http://127.0.0.1:8080/db/guillotina/@sharing"
```

and create actual content:

```
  curl -X POST -H "Accept: application/json" --user root:root -H "Content-Type: application/json" -d '{
    "@type": "Item",
    "title": "News",
    "id": "news"
  }' "http://127.0.0.1:8080/db/guillotina/"
```

# Quickstart

How to quickly get started using `guillotina`.

This tutorial will assume usage of virtualenv. You can use your own preferred
tool for managing your python environment.


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
./bin/pcreate configuration
```

Finally, run the server:

```
./bin/guillotina
```

The server should now be running on http://0.0.0.0:8080

Then, [use Postman](https://www.getpostman.com/), curl or whatever tool you
prefer to interact with the REST API.

Modify the configuration in config.json to customize server setttings.


## Creating default content

Once started, you will require to add at least a Guillotina site to start fiddling around:

```
  curl -X POST -H "Accept: application/json" --user root:root -H "Content-Type: application/json" -d '{
    "@type": "Site",
    "title": "Guillotina 1",
    "id": "guillotina",
    "description": "Description"
  }' "http://127.0.0.1:8080/zodb1/"
```

and give permissions to add content to it:

```
  curl -X POST -H "Accept: application/json" --user root:root -H "Content-Type: application/json" -d '{
    "prinrole": {
        "Anonymous User": ["guillotina.Member", "guillotina.Reader"]
    }
  }' "http://127.0.0.1:8080/zodb1/guillotina/@sharing"
```

and create actual content:

```
  curl -X POST -H "Accept: application/json" --user root:root -H "Content-Type: application/json" -d '{
    "@type": "Item",
    "title": "News",
    "id": "news"
  }' "http://127.0.0.1:8080/zodb1/guillotina/"
```

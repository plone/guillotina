# Quickstart

How to quickly get started using `plone.server`.

This tutorial will assume usage of virtualenv. You can use your own preferred
tool for managing your python environment.


Setup the environment:

```
virtualenv .
```

Install `plone.server`:

```
./bin/pip install plone.server
```

Generate configuration file:

```
./bin/pcreate configuration
```

Finally, run the server:

```
./bin/pserver
```

The server should now be running on http://0.0.0.0:8080

Then, [use Postman](https://www.getpostman.com/), curl or whatever tool you
prefer to interact with the REST API.

Modify the configuration in config.json to customize server setttings.


## Creating default content

Once started, you will require to add at least a Plone site to start fiddling around:

```
  curl -X POST -H "Accept: application/json" --user root:root -H "Content-Type: application/json" -d '{
    "@type": "Site",
    "title": "Plone 1",
    "id": "plone",
    "description": "Description"
  }' "http://127.0.0.1:8080/zodb1/"
```

and give permissions to add content to it:

```
  curl -X POST -H "Accept: application/json" --user root:root -H "Content-Type: application/json" -d '{
    "prinrole": {
        "Anonymous User": ["plone.Member", "plone.Reader"]
    }
  }' "http://127.0.0.1:8080/zodb1/plone/@sharing"
```

and create actual content:

```
  curl -X POST -H "Accept: application/json" --user root:root -H "Content-Type: application/json" -d '{
    "@type": "Item",
    "title": "News",
    "id": "news"
  }' "http://127.0.0.1:8080/zodb1/plone/"
```

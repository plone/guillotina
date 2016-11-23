Introduction
============

This is the working project of the next generation plone server based on asyncio.

* depends on python 3.5


Getting started
---------------

We use buildout of course::

    python3.5 bootstrap-buildout.py
    ./bin/buildout

The buildout installs the app itself, code analysis tools, and a test runner.

Run the zeo
-----------

To run the zeo on a different terminal::

	./bin/runzeo -C zeo.cfg


Run the server
--------------

* By default it mounts a zeo server and a ZODB so you need the ZEO server running.

To run the server::

    ./bin/server

Creating default content
------------------------

Once started, you will require to add at least a Plone site to start fiddling around::

  curl -X POST -H "Accept: application/json" --user root:root -H "Content-Type: application/json" -d '{
    "@type": "Site",
    "title": "Plone 1",
    "id": "plone",
    "description": "Description"
  }' "http://127.0.0.1:8080/zodb1/"

and give permissions to add content to it::

  curl -X POST -H "Accept: application/json" --user root:root -H "Content-Type: application/json" -d '{
    "prinrole": {
        "Anonymous User": ["plone.Member", "plone.Reader"]
    }
  }' "http://127.0.0.1:8080/zodb1/plone/@sharing"

and create actual content::

  curl -X POST -H "Accept: application/json" --user root:root -H "Content-Type: application/json" -d '{
    "@type": "Item",
    "title": "News",
    "id": "news"
  }' "http://127.0.0.1:8080/zodb1/plone/"

Run tests
---------

We're using py.test::

    ./bin/py.test src

and for test coverage::

    ./bin/py.test --cov=plone.server src/


Default
-------

Default root access can be done with AUTHORIZATION header : Basic admin


Running dependency graph
------------------------

Using buildout::

    ./bin/buildout -c dependency-graph.cfg
    ./bin/dependencies-eggdeps > docs/dependency-graph.txt

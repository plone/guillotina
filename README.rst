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

Run tests
---------

We're using py.test::

    ./bin/py.test src

and for test coverage::

    ./bin/py.test --cov=plone.server src/


Default
-------

Default root access can be done with AUTHORIZATION header : Basic YWRtaW4=


Postman tests
-------------

* It tests performance against ZODB and ZEO mount points

npm install -g newman
newman -c tests.json

Running dependency graph
------------------------

Using buildout::

    ./bin/buildout -c dependency-graph.cfg
    ./bin/dependencies-eggdeps > docs/dependency-graph.txt

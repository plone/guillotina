Introduction
============

This is the working project of the next generation plone server based on asyncio.

* depends on python 3.5

Please `read the detailed docs <http://ploneserver.readthedocs.io/en/latest/>`_


Getting started with development
--------------------------------

We use buildout of course::

    virtualenv .
    ./bin/pip install zc.buildout
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

Default root access can be done with AUTHORIZATION header : Basic root:root

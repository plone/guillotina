Introduction
============

This is the working project of the next generation plone server based on asyncio.

* depends on python 3.5


Getting started
---------------

We use buildout of course::

    python3.5 bootstrap.py
    # then run the server
    ./bin/sandbox


Run tests
---------

We're using py.test::

    ./bin/py.test src

Introduction
============

.. image:: https://img.shields.io/badge/docs-latest-brightgreen.svg?style=flat
   :target: http://guillotina.readthedocs.io/en/latest/

.. image:: https://travis-ci.org/plone/guillotina.svg?branch=master
   :target: https://travis-ci.org/plone/guillotina

.. image:: https://img.shields.io/pypi/v/guillotina.svg
   :target: https://pypi.python.org/pypi/guillotina

Please `read the detailed docs <http://guillotina.readthedocs.io/en/latest/>`_


This is the working project of the next generation Guillotina server based on asyncio.

* depends on python >= 3.5

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

    ./bin/py.test --cov=guillotina src/


Default
-------

Default root access can be done with AUTHORIZATION header : Basic root:root

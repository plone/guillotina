Introduction
============

.. image:: https://img.shields.io/badge/docs-latest-brightgreen.svg?style=flat
   :target: http://guillotina.readthedocs.io/en/latest/

.. image:: https://travis-ci.org/plone/guillotina.svg?branch=master
   :target: https://travis-ci.org/plone/guillotina

.. image:: https://codecov.io/gh/plone/guillotina/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/plone/guillotina/branch/master
   :alt: Test Coverage

.. image:: https://img.shields.io/pypi/pyversions/guillotina.svg
   :target: https://pypi.python.org/pypi/guillotina/
   :alt: Python Versions

.. image:: https://img.shields.io/pypi/v/guillotina.svg
   :target: https://pypi.python.org/pypi/guillotina

.. image:: https://img.shields.io/pypi/l/guillotina.svg
   :target: https://pypi.python.org/pypi/guillotina/
   :alt: License

.. image:: https://badges.gitter.im/plone/guillotina.png
   :target: https://gitter.im/plone/guillotina
   :alt: Chat

Please `read the detailed docs <http://guillotina.readthedocs.io/en/latest/>`_


This is the working project of the next generation Guillotina server based on asyncio.


Dependencies
------------

* python >= 3.6
* postgresql >= 9.6


Quickstart
----------

We use pip::

  pip install guillotina


Run postgresql
--------------

If you don't have a postgresql server to play with, you can run one easily
with docker.

Download and start the docker container by running::

  make run-postgres



Run the server
--------------

To run the server::

    g


Then...

    curl http://localhost:8080


Or, better yet, use postman to start playing with API.

You can also navigate in your Guillotina server with its built-in web admin interface by visiting http://localhost:8080/+admin/.

Deploy on Heroku
----------------

Read more `Guillotina-Heroku <https://github.com/guillotinaweb/guillotina-heroku>`_.

.. image:: https://www.herokucdn.com/deploy/button.svg
   :target: https://www.heroku.com/deploy?template=https://github.com/guillotinaweb/guillotina-heroku

Getting started with development
--------------------------------

Using pip(requires python > 3.6)::

  git clone git@github.com:plone/guillotina.git
  cd guillotina
  python -m venv .
  ./bin/pip install -r requirements.txt
  ./bin/pip install -e .[test]


Run tests
---------

We're using pytest::

    ./bin/pytest guillotina

and for test coverage::

    ./bin/pytest --cov=guillotina guillotina/

With file watcher...

    ./bin/ptw guillotina --runner=./bin/py.test


To run tests with cockroach db::

   USE_COCKROACH=true ./bin/pytest guillotina

Default
-------

Default root access can be done with AUTHORIZATION header : Basic root:root


Docker
------

You can also run Guillotina with Docker!


First, run postgresql::

    docker run --rm \
        -e POSTGRES_DB=guillotina \
        -e POSTGRES_USER=guillotina \
        -p 127.0.0.1:5432:5432 \
        --name postgres \
        postgres:9.6

Then, run guillotina::

    docker run --rm -it \
        --link=postgres -p 127.0.0.1:8080:8080 \
        guillotina/guillotina:latest \
        g -c '{"databases": [{"db": {"storage": "postgresql", "dsn": "postgres://guillotina:@postgres/guillotina"}}], "root_user": {"password": "root"}}'


This assumes you have a config.yaml in your current working directory


Chat
----

Join us to talk about Guillotina at https://gitter.im/plone/guillotina

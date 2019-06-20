# Installing Guillotina

Guillotina is a simple Python package so it can be installed with any of the
number of installation methods available to Python.

In the traing here, we will focus on using [pip](https://pip.pypa.io/en/stable/)
and docker. You can use, for example, buildout as well.


## with pip

```eval_rst
.. note::
   It is recommended you install along with a venv::

      python3.7 -m venv genv
      cd genv
      source ./bin/activate
```


It's as simple as...

```
pip install guillotina
```


For the purpose of this training, you'll also need to install `cookiecutter`.

```
pip install cookiecutter
```


Guillotina also provides [docker images](https://hub.docker.com/r/guillotina/guillotina/).


**References**

  - [Quickstart](../../quickstart)
  - [Installation](../../installation/index)
  - [About Guillotina](../../about)

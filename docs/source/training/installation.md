# Installing Guillotina

To install Guillotina, we will use [pip](https://pip.pypa.io/en/stable/ "Link to pip's website")
and [Docker](https://www.docker.com/ "Link to Docker's website").

Please make sure that you have both installed.

```eval_rst
.. note:: It is recommended you install along with a `virtual environment <https://docs.python.org/3/library/venv.html>`_
```

```shell
python3.7 -m venv genv
cd genv
source ./bin/activate
```

```shell
pip install guillotina
```

For the purpose of this training, you'll also need to install
[Cookiecutter](https://cookiecutter.readthedocs.io/en/latest/ "Link to Cookiecutter's website").

```shell
pip install cookiecutter
```

**References**

  - [Quickstart](../../quickstart)
  - [Installation](../../installation/index)
  - [About Guillotina](../../about)

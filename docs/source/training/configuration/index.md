# Configuration

```eval_rst
.. toctree::
   :maxdepth: 2

   .
   advanced
```

You may have wondered how running `g` command without any configuration and
options knew to connect and configure the database. Well, it's only because
we provide default settings in our application and documentation to make
that step easy.

In this section, we'll talk about working with the Guillotina configuration
system.


## Getting started

Guillotina provides a command to bootstrap a configuration file for you.

```eval_rst
.. warning::
   You need to install cookiecutter in order to use templates:
    
    pip install cookiecutter
```

```
g create --template=configuration
```

This will produce a `config.yaml` file in your current path. Inspect the file
to see what some of the default configuration options are.

## Database configuration

The example config.yaml file that is produced provides a sample for PostgreSQL, so before we continue,
we'll need to run a postgresql server for Guillotina to use.

```
docker run -e POSTGRES_DB=guillotina -e POSTGRES_USER=guillotina -p 127.0.0.1:5432:5432 postgres:9.6
```

```eval_rst
.. note::
   This particular docker run command produces a volatile database. Stopping and
   starting it again will cause you to lose any data you pushed into it.
```

## Modifying configuration

A detailed list of configuration options and explanations can be found
in the [configuration section](../../installation/configuration.html) of the docs.


```eval_rst
.. note:: Guillotina also supports JSON configuration files
```

## Configuration file

To specify a configuration file other than the name `config.yaml`, you can use
the `-c` or `--config` command line option.


```
g -c config-foobar.yaml
```


## Installing applications

Guillotina applications are python packages that you install and then configure
in your application settings.

For an example, we'll go through installing swagger support.

```
pip install guillotina_swagger
```

Then, add this to your `config.yaml` file.

```yaml
applications:
- guillotina_swagger
```

Finally, start Guillotina again and visit `http://localhost:8080/@docs`.


**References**

  - [Configuration Options](../../installation/configuration)

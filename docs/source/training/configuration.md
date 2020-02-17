# Configuration

You may have wondered how running `g` command without any configuration and
options knew to connect and configure the database. This is because Guillotina
will run without configuration. In it's place, it will run with a DUMMY_FILE
database which will save the database file locally.

In this section, we'll talk about working with the Guillotina configuration
system and configure Guillotina to run with a postgresql database.


## Getting started

Guillotina provides a command to bootstrap a configuration file for you.

```
g create --template=configuration
```

This will produce a `config.yaml` file in your current path. Inspect the file
to see what some of the default configuration options are.

## Modifying configuration

A detailed list of configuration options and explanations can be found
in the [configuration section](../../installation/configuration.html) of the docs.


```eval_rst
.. note:: Guillotina also supports JSON configuration files
```

## Running PostgreSQL

Next, you'll need to run a [PostgreSQL](https://www.postgresql.org/ "Link to PostgreSQL's website")
server for Guillotina to use.

``` shell
docker run \
  -e POSTGRES_DB=guillotina -e POSTGRES_USER=postgres \
  -p 127.0.0.1:5432:5432 \
  postgres:9.6
```


```eval_rst
.. warning::
   This particular docker run command produces a volatile database.

   Stopping and starting it again will cause you to lose any data you pushed into it.
```

## Configuration file

To specify a configuration file other than the name `config.yaml`, you can use
the `-c` or `--config` command line option.


```
g -c config-foobar.yaml
```

```eval_rst
.. note::
   Make sure your configuration matches your PostgreSQL server settings
```


## Installing applications

Guillotina applications are python packages or modules that you install and then configure
in your application settings.

For an example, we'll go through activating swagger support.

Since version 5, swagger is in packaged with Guillotina by default.

Make sure `guillotina.contrib.swagger` is listed in your `config.yaml` file.

```yaml
applications:
- guillotina.contrib.swagger
```

Finally, start Guillotina again and visit `http://localhost:8080/@docs`.


**References**

  - [Configuration Options](../../installation/configuration)

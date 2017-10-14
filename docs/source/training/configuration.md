# Configuration

You may have wondered how running `g` command without any configuration and
options knew to connect and configure the database. Well, it's only because
we provide default settings in our application and documentation to make
that step easy.

In this section, we'll talk about working with the Guillotina configuration
system.


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

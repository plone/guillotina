# Applications

Applications are used to provide additional functionality to plone.server.

## Community Addons

Some useful addons to use in your own development:

- [pserver.elasticsearch](https://github.com/pyrenees/pserver.elasticsearch): Index content in elastic search
- [pserver.zodbusers](https://github.com/pyrenees/pserver.zodbusers): Store and authenticate users in the database
- [pserver.mailer](https://github.com/pyrenees/pserver.mailer): async send mail


## Creating

An application is a python package that implements an entry point to tell plone.server
to load it.

If you're not familiar with how to build python applications, please
[read documentation on building packages](https://python-packaging.readthedocs.io/en/latest/)
before you continue on.

In your setup.py file, include an entry point like this for your application:

```python
  setup(
    entry_points={
      'plone.server': [
          'include = pserver.myaddon',
      ]
  })
```

In this example, `pserver.myaddon` is your package module.


## Initialization

Creating the `plone.server` entry point only tells `plone.server` that your
application is available to be used. Your `config.json` file will also need
to provide the application name in the `applications` array for it to be initialized.


```json
{
  "applications": ["pserver.elasticsearch"]
}
```


## Configuration

Once you create a `plone.server` application, there are three primary ways for it
to hook into `plone.server`.


### Call includeme function

Your application can provide an `includeme` function at the root of the module
and `plone.server` will call it with the instance of the `root` object.

```python

def includeme(root):
  # do initialization here...
  pass
```

### Load app_settings

If an `app_settings` dict is provided at the module root, it will automatically
merge the global `plone.server` app_settings with the module's. This allows you
to provide custom configuration.


### ZCML

If you're application is activated and has a `configure.zcml` file in it, it
will automatically be loaded.

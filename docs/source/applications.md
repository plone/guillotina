# APPLICATIONS

Applications are used to provide additional functionality to plone.server.


## CREATING AN APPLICATION

An application is a python package that implements an entry point to tell plone.server
to load it.

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


## APPLICATION INITIALIZATION

Creating the `plone.server` entry point only tells `plone.server` that your
application is available to be used. Your `config.json` file will also need
to provide the application name in the `applications` array for it to be initialized.


```json
{
  "applications": ["pserver.elasticsearch"]
}
```


## APPLICATION CONFIGURATION

Once you create a `plone.server` application, there are three primary ways for it
to hook into `plone.server`.


### LOAD ZCML

If you're application is activated and has a `configure.zcml` file in it, it
will automatically be loaded.


### CALL INCLUDEME FUNCTION

Your application can provide an `includeme` function at the root of the module
and `plone.server` will call it with the instance of the `root` object.

```python

def includeme(root):
  # do initialization here...
  pass
```

### LOAD APP_SETTINGS

If an `app_settings` dict is provided at the module root, it will automatically
merge the global `plone.server` app_settings with the module's. This allows you
to provide custom configuration.

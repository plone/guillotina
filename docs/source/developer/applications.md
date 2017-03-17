# Applications

Applications are used to provide additional functionality to guillotina.

## Community Addons

Some useful addons to use in your own development:

- [pserver.elasticsearch](https://github.com/pyrenees/pserver.elasticsearch): Index content in elastic search
- [pserver.zodbusers](https://github.com/pyrenees/pserver.zodbusers): Store and authenticate users in the database
- [pserver.mailer](https://github.com/pyrenees/pserver.mailer): async send mail


## Creating

An application is a python package that implements an entry point to tell guillotina
to load it.

If you're not familiar with how to build python applications, please
[read documentation on building packages](https://python-packaging.readthedocs.io/en/latest/)
before you continue on.

In this example, `guillotina_myaddon` is your package module.


## Initialization

Your `config.json` file will need to provide the application name in the
`applications` array for it to be initialized.


```json
{
  "applications": ["guillotina_myaddon"]
}
```


## Configuration

Once you create a `guillotina` application, there are two primary ways for it
to hook into `guillotina`.


### Call includeme function

Your application can provide an `includeme` function at the root of the module
and `guillotina` will call it with the instance of the `root` object.

```python

def includeme(root):
  # do initialization here...
  pass
```

### Load app_settings

If an `app_settings` dict is provided at the module root, it will automatically
merge the global `guillotina` app_settings with the module's. This allows you
to provide custom configuration.

# Applications

Applications are used to provide additional functionality to Guillotina.


## Core Addons

- `guillotina.contrib.swagger`: Activate swagger support at `/@docs`.
- `guillotina.contrib.catalog.pg`: Provide search functionality with PostgreSQL queries.
- `guillotina.contrib.cache`: Cache support for guillotina.
- `guillotina.contrib.redis`: Cache support for guillotina using redis with invalidation across multiple instances.
- `guillotina.contrib.pubsub`: Pubsub support for guillotina
- `guillotina.contrib.mailer`: Send email with guillotina


## Community Addons

Some useful addons to use in your own development:

- [guillotina_elasticsearch](https://github.com/guillotinaweb/guillotina_elasticsearch/): Index content in elastic search
- [guillotina_dbusers](https://github.com/guillotinaweb/guillotina_dbusers): Store and authenticate users in the database


## Creating

An application is a Python package that implements an entry point to tell Guillotina
to load it.

If you're not familiar with how to build Python applications, please
[read documentation on building packages](https://python-packaging.readthedocs.io/en/latest/)
before you continue.

In this example, `guillotina_myaddon` is your package module.


## Initialization

Your `config.yaml` file will need to provide the application name in the
`applications` array for it to be initialized.


```yaml
applications:
    - guillotina_myaddon

```


## Configuration

Once you create a Guillotina application, there are two primary ways for it
to hook into Guillotina.


### Call the `includeme` function

Your application can provide an `includeme` function at the root of the module
and Guillotina will call it with the instance of the `root` object.

```python

def includeme(root):
  # do initialization here...
  pass
```

### Load `app_settings`

If an `app_settings` dict is provided at the module root, it will automatically
merge the global Guillotina `app_settings` with the module's. This allows you
to provide custom configuration.

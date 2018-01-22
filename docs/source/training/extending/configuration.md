# Configuration

All application extension configuration is defined with Guillotina's `configure`
module and the `app_settings` object.

Defining content types, behaviors, services, etc all require the use of the
`configure` module. Guillotina reads all the registered configuration in code
for each install application and loads it.

## app_settings

Guillotina also provides a global `app_settings` object::

```python
from guillotina import app_settings
```

This object contains all the settings from your `config.yaml` file as well as
any additional configuration settings defined in addons.

`app_settings` has an order of precedence it will use pick settings from:

 - guillotina's default settings
 - each application in order it is defined can override default guillotina settings
 - config.yaml takes final precedence over all configuration

`app_settings` has an extra key '__file__' that contains the path of the
configuration file, allowing relative paths to be used in an application
settings.

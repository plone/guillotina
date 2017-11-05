# Logging

Logging configuration is built into `guillotina`'s configuration syntax.

If the `logging` setting is provided, it is simply passed to Python's `dict` config
method: https://docs.python.org/3.6/library/logging.config.html#logging-config-dictschema


## Example guillotina configuration

To log errors for guillotina for example:

```json
{
  "logging": {
    "version": 1,
    "formatters": {
      "brief": {
        "format": "%(message)s"
      },
      "default": {
        "format": "%(asctime)s %(levelname)-8s %(name)-15s %(message)s",
        "datefmt": "%Y-%m-%d %H:%M:%S"
      }
    },
    "handlers": {
      "file": {
        "class": "logging.handlers.RotatingFileHandler",
        "formatter": "default",
        "filename": "logconfig.log",
        "maxBytes": 1024,
        "backupCount": 3
      }
    },
    "loggers": {
      "guillotina": {
        "level": "DEBUG",
        "handlers": ["file"],
        "propagate": 0
      }
    }
  }
}
```


## Request logging example

```json
{
  "logging": {
    "version": 1,
    "formatters": {
      "default": {
        "format": "%(message)s"
      }
    },
    "handlers": {
      "file": {
        "class": "logging.handlers.RotatingFileHandler",
        "formatter": "default",
        "filename": "access.log",
        "maxBytes": 1024,
        "backupCount": 3
      }
    },
    "loggers": {
      "aiohttp.access": {
        "level": "INFO",
        "handlers": ["file"],
        "propagate": 0
      }
    }
  }
}
```


## Available Loggers

- `guillotina`
- `aiohttp.access`
- `aiohttp.client`
- `aiohttp.internal`
- `aiohttp.server`
- `aiohttp.web`
- `aiohttp.websocket`

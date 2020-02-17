# Swagger

Guillotina provides out of the box OpenAPI (Swagger) support.

## Configuration

```yaml
applications:
- guillotina.contrib.swagger
```

## Usage

Once activated, visit `http://localhost:8080/@docs` to view OpenAPI documentation.

Make sure to click the `Authenticate` button to specify the root location to load the OpenAPI definitions.

.. note::

    You need to provide username/password to authenticate with.

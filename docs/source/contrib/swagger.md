# Swagger

Guillotina provides out of the box swagger support.


## Configuration

```yaml
applications:
- guillotina.contrib.swagger
```

## Usage


Once activated, visit `http://localhost:8080/@docs` to view swagger documentation.

Make sure to click the `Authenticate` button to specify root location to load swagger
definitions for and provide username/password to authenticate with.

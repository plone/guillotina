# JSONb Catalog

`guillotina` provides out of the box support for searching content via postgresql jsonb serialized data.


## Configuration

To install, add the pg catalog contrib package

```yaml
applications:
- guillotina.contrib.catalog.pg
```

Once installed, you will be able to search content using the `@search` endpoint.

(hint: also add `guillotina.contrib.swagger` to read swagger docs on endpoints)

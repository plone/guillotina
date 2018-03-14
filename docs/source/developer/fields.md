# Fields

Guillotina uses schemas to define content types and behaviors. These schemas
consist of field definitions.


## Available fields

- guillotina.schema.Bool
- guillotina.schema.Bytes
- guillotina.schema.Choice: validates against vocabulary of values
- guillotina.schema.Date
- guillotina.schema.Datetime
- guillotina.schema.Decimal
- guillotina.schema.Dict
- guillotina.schema.Float
- guillotina.schema.Int
- guillotina.schema.JSONField
- guillotina.schema.List
- guillotina.schema.Set
- guillotina.schema.Text
- guillotina.schema.TextLine
- guillotina.schema.Time
- guillotina.fields.PatchField: allow updating value without patching entire value
- guillotina.fields.BucketListField: optimized storage for very large lists of data


## Patch field

Guillotina provides a `PatchField` which allows you to patch values of `List` and
`Dict` fields without having the original value.

### Patch list field


```python
from zope.interface import Interface
from guillotina.fields import PatchField
from guillotina import schema

class IMySchema(Interface):
    values = PatchField(schema.List(
        value_type=schema.Text()
    ))
```

Then, payload for patching to append to this list would look like:

```json
{
    "values": {
        "op": "append",
        "value": "foobar"
    }
}
```

Extend:

```json
{
    "values": {
        "op": "extend",
        "value": ["foo", "bar"]
    }
}
```

Delete:

```json
{
    "values": {
        "op": "del",
        "value": 0
    }
}
```

Update:

```json
{
    "values": {
        "op": "update",
        "value": {
            "index": 0,
            "value": "Something new"
        }
    }
}
```


### Patch dict field


```python
from zope.interface import Interface
from guillotina.fields import PatchField
from guillotina import schema

class IMySchema(Interface):
    values = PatchField(schema.Dict(
        key_type=schema.Text()
        value_type=schema.Text()
    ))
```

Then, payload for patching to add to this dict would look like:

```json
{
    "values": {
        "op": "assign",
        "value": {
            "key": "foo",
            "value": "bar"
        }
    }
}
```

Delete:

```json
{
    "values": {
        "op": "del",
        "value": "foo"
    }
}
```


### Bucket list field

```python
from zope.interface import Interface
from guillotina.fields import PatchField
from guillotina import schema

class IMySchema(Interface):
    values = BucketListField(
        value_type=schema.Text(),
        bucket_len=5000
    )
```


Then, payload for patching to append to this list would look like:

```json
{
    "values": {
        "op": "append",
        "value": "foobar"
    }
}
```

Extend:

```json
{
    "values": {
        "op": "extend",
        "value": ["foo", "bar"]
    }
}
```

Delete:

```json
{
    "values": {
        "op": "del",
        "value": {
            "bucket_index": 0,
            "item_index": 0
        }
    }
}
```

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
- guillotina.fields.BucketDictField: optimized storage for very large dictionaries of data
- guillotina.files.CloudFileField: file field for storing in db or cloud storage


## Patch field

Guillotina provides a `PatchField` which allows you to patch values of
`List`, `Dict` and `Int` fields without having the original value.
This is done doing a PATCH request to the object absolute url with
the following payloads:


### Patch field list


```python
from zope.interface import Interface
from guillotina.fields import PatchField
from guillotina import schema

class IMySchema(Interface):
    field = PatchField(schema.List(
        value_type=schema.Text()
    ))
```

Then, payload for patching to append to this list would look like:


```json
{
    "field": {
        "op": "append",
        "value": "foobar"
    }
}
```


Append if unique value only:

```json
{
    "field": {
        "op": "appendunique",
        "value": "foobar"
    }
}
```

Extend:

```json
{
    "field": {
        "op": "extend",
        "value": ["foo", "bar"]
    }
}
```

Extend if unique values:

```json
{
    "field": {
        "op": "extendunique",
        "value": ["foo", "bar"]
    }
}
```

Delete:

```json
{
    "field": {
        "op": "del",
        "value": 0
    }
}
```

Remove:

```json
{
    "field": {
        "op": "remove",
        "value": "foobar"
    }
}
```

Update:

```json
{
    "field": {
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
    field = PatchField(schema.Dict(
        key_type=schema.Text(),
        value_type=schema.Text()
    ))
```

Then, payload for patching to add to this dict would look like:

```json
{
    "field": {
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
    "field": {
        "op": "del",
        "value": "foo"
    }
}
```

Update:

```json
{
    "values": {
        "op": "update",
        "field": [{
            "key": "foo",
            "value": "bar"
        }, {
            "key": "foo2",
            "value": "bar2"
        }]
    }
}
```


### Patch int field


`PatchField` can also be used on `Int` fields to increment, decrement
or reset their original value.

```python
from zope.interface import Interface
from guillotina.fields import PatchField
from guillotina import schema

class IMySchema(Interface):
    counter = PatchField(schema.Int(
        title='My Counter',
        default=1,
    ))
```

The payload to increment `counter` by 3 units would look like:

```json
{
    "counter": {
        "op": "inc",
        "value": 3
    }
}
```

Notice that, at this point, `counter` will be set to 4 because its
default value is 1. If the default would not be set, the increment
operation assumes a 0, and thus `counter` would be 3.

Likewise, to decrement the field, the following payload would work:

```json
{
    "counter": {
        "op": "dec",
        "value": 4
    }
}
```

To reset `counter` to its default value, you can send the following
payload without `value`:

```json
{
    "counter": {
        "op": "reset"
    }
}
```

and `counter` will be set to its default value 1. Otherwise, you can
also send the target reset value:

```json
{
    "counter": {
        "op": "reset",
        "value": 0
    }
}
```

Notice that a reset operation on a integer without a default value is
equivalent to sending a value of 0.


### Bucket list field

```python
from zope.interface import Interface
from guillotina.fields import BucketListField
from guillotina import schema

class IMySchema(Interface):
    field = BucketListField(
        value_type=schema.Text(),
        bucket_len=5000
    )
```


Then, payload for patching to append to this list would look like:

```json
{
    "field": {
        "op": "append",
        "value": "foobar"
    }
}
```

Extend:

```json
{
    "field": {
        "op": "extend",
        "value": ["foo", "bar"]
    }
}
```

Delete:

```json
{
    "field": {
        "op": "del",
        "value": {
            "bucket_index": 0,
            "item_index": 0
        }
    }
}
```


## Bucket dict field

```python
from zope.interface import Interface
from guillotina.fields import BucketDictField
from guillotina import schema

class IMySchema(Interface):
    field = BucketDictField(
        key_type=schema.Text(),
        value_type=schema.Text(),
        bucket_len=5000
    )
```


Then, payload for patching would be...:

```json
{
    "field": {
        "op": "assign",
        "value": {
            "key": "foo",
            "value": "bar"
        }
    }
}
```

Update:

```json
{
    "field": {
        "op": "update",
        "value": [{
            "key": "foo",
            "value": "barupdated"
        }, {
            "key": "other",
            "value": "othervalue"
        }]
    }
}
```

Delete:

```json
{
    "field": {
        "op": "del",
        "value": "foo"
    }
}
```

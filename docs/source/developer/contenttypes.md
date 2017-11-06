# Content types

Content types allow you to provide custom schemas and content to your services.

Out-of-the-box, `guillotina` ships with simple `Container`, `Folder` and `Item` content types.
The `Container` content type is the main content type to hold your data in. It is
the starting point for applications and other things to operate within.

The `Folder` type allows someone to add items inside of it. Both types only have
simple Dublin Core fields by default.


## Defining content types

A content type consists of a class and optionally, a schema to define the custom
fields you want your class to use.

A simple type will look like this::

```python
from guillotina import configure
from guillotina.content import Folder
from guillotina.interfaces import IItem
from guillotina import schema

class IMySchema(IItem):
    foo = schema.Text()

@configure.contenttype(
    type_name="MyType",
    schema=IMySchema,
    behaviors=["guillotina.behaviors.dublincore.IDublinCore"])
class MyType(Folder):
    pass
```

This example creates a simple schema and assigns it to the `MyType` content
type.


```eval_rst
.. include:: ./_scanning.rst
```

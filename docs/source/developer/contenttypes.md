# Content types

Content types allow you to provide custom schemas and content to your services.

OOTB, `guillotina` ships with simple `Folder` and `Item` content types. The
`Folder` type allowing someone to add items inside of it. Both types only have
simple dublin core fields.


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


**Scanning**
If your service modules are not imported at run-time, you may need to provide an
additional scan call to get your services noticed by `guillotina`.

In your application `__init__.py` file, you can simply provide a `scan` call.

```python
from guillotina import configure

def includeme(root):
    configure.scan('my.package.content')
```

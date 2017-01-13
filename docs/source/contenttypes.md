# Content types

Content types allow you to provide custom schemas and content to your services.

OOTB, `plone.server` ships with simple `Folder` and `Item` content types. The
`Folder` type allowing someone to add items inside of it. Both types only have
simple dublin core fields.


## Defining content types

A content type consists of a class and optionally, a schema to define the custom
fields you want your class to use.

A simple type will look like this::

```python
from plone.server import configure
from plone.server.content import Folder
from plone.server.interfaces import IItem
from zope import schema

class IMySchema(IItem):
    foo = schema.Text()

@configure.contenttype(
    portal_type="MyType",
    schema=IMySchema,
    behaviors=["plone.server.behaviors.dublincore.IDublinCore"])
class MyType(Folder):
    pass
```

This example creates a simple schema and assigns it to the `MyType` content
type.


**Scanning**
If your service modules are not imported at run-time, you may need to provide an
additional scan call to get your services noticed by `plone.server`.

In your application `__init__.py` file, you can simply provide a `scan` call.

```python
from plone.server import configure

def includeme(root):
    configure.scan('my.package.content')
```

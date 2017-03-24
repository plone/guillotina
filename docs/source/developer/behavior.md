# Behaviors

Besides having static content type definition with its schema there is the concept of behaviors that provide us cross-content type definitions with specific marker interface to create adapters and subscribers based on that behavior and not the content type.

## Definition of a behavior

If you want to have a shared behavior based on some fields and operations that needs to be shared across different content you can define them on a guillotina.schema interface:

```python
    from guillotina.interfaces import IFormFieldProvider
    from zope.interface import Interface
    from zope.interface import provider
    from guillotina.schema import Textline

    @provider(IFormFieldProvider)
    class IMyLovedBehavior(Interface):
        text = Textline(
            title=u'Text line field',
            required=False
        )

        text2 = Textline(
            title=u'Text line field',
            required=False
        )

```

Once you define the schema you can define a specific marker interface that will be applied to the objects that has this behavior:

```python

    class IMarkerBehavior(Interface):
        """Marker interface for content with attachment."""

```

Finally the instance class that implements the schema can be defined in case you want to enable specific operations or you can use guillotina.behaviors.instance.AnnotationBehavior as the default annotation storage.

For example in case you want to have a class that stores the field on the content and not on annotations:

```python
from guillotina.behaviors.properties import ContextProperty
from guillotina.behaviors.instance import AnnotationBehavior
from guillotina.interfaces import IResource
from guillotina import configure

@configure.behavior(
    title="Attachment",
    provides=IMyLovedBehavior,
    marker=IMarkerBehavior,
    for_=IResource)
class MyBehavior(AnnotationBehavior):
    """If attributes
    """
    text = ContextProperty(u'attribute', ())
```

On this example text will be stored on the context object and text2 as a annotation.


## Static behaviors

With behaviors you can define them as static for specific content types:

```python

from guillotina import configure
from guillotina.interfaces import IItem
from guillotina.content import Item

@configure.contenttype(
    type_name="MyItem",
    schema=IItem,
    behaviors=["guillotina.behaviors.dublincore.IDublinCore"])
class MyItem(Item):
    pass
```

**Scanning**
If your service modules are not imported at run-time, you may need to provide an
additional scan call to get your services noticed by `guillotina`.

In your application `__init__.py` file, you can simply provide a `scan` call.

```python
from guillotina import configure

def includeme(root):
    configure.scan('my.package.services')
```


### Create and modify content with behaviors

On the deserialization of the content you will need to pass on the POST/PATCH operation the behavior as a object on the JSON.


CREATE an ITEM with the expires : POST on parent:

```json
    {
        "@type": "Item",
        "guillotina.behaviors.dublincore.IDublinCore": {
            "expires": "1/10/2017"
        }
    }
```

MODIFY an ITEM with the expires : PATCH on the object:

```json
    {
        "guillotina.behaviors.dublincore.IDublinCore": {
            "expires": "1/10/2017"
        }
    }
```

### Get content with behaviors

On the serialization of the content you will get the behaviors as objects on the content.

GET an ITEM : GET on the object:

```json
    {
        "@id": "http://localhost:8080/zodb/guillotina/item1",
        "guillotina.behaviors.dublincore.IDublinCore": {
            "expires": "2017-10-01T00:00:00.000000+00:00",
            "modified": "2016-12-02T14:14:49.859953+00:00",
        }
    }
```


## Dynamic Behaviors

guillotina offers the option to have content that has dynamic behaviors applied to them.

### Which behaviors are available on a context

We can know which behaviors can be applied to a specific content.

GET CONTENT_URI/@behaviors:

```json

    {
        "available": ["guillotina.behaviors.attachment.IAttachment"],
        "static": ["guillotina.behaviors.dublincore.IDublinCore"],
        "dynamic": [],
        "guillotina.behaviors.attachment.IAttachment": { },
        "guillotina.behaviors.dublincore.IDublinCore": { }
    }
```

This list of behaviors is based on the for statement on the configure of the behavior.
The list on static are the ones defined on the content type definition on the configure.
The list on dynamic are the ones that have been assigned.

### Add a new behavior to a content

We can add a new dynamic behavior to a content by a PATCH operation on the object with the @behavior attribute or in a small PATCH operation to @behavior entry point with the value to add.

MODIFY an ITEM with the expires : PATCH on the object:

```json

    {
        "guillotina.behaviors.dublincore.IDublinCore": {
            "expires": "1/10/2017"
        }
    }
```

MODIFY behaviors : PATCH on the object/@behaviors:

```json
    {
        "behavior": "guillotina.behaviors.dublincore.IDublinCore"
    }
```

### Delete a behavior to a content

We can add a new dynamic behavior to a content by a DELETE operation to @behavior entry point with the value to remove.

DELETE behaviors : DELETE on the object/@behaviors:

```json
    {
        "behavior": "guillotina.behaviors.dublincore.IDublinCore"
    }
```

# Behaviors

Besides having static content type definition with its schema there is the concept of behaviors that provide us cross-content type definitions with specific marker interface to create adapters and subscribers based on that behavior and not the content type.

## Definition of a behavior

If you want to have a shared behavior based on some fields and operations that needs to be shared across different content you can define them on a zope.schema interface:

```python
    from plone.server.interfaces import IFormFieldProvider
    from zope.interface import Interface
    from zope.interface import provider
    from zope.schema import Textline

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

Finally the instance class that implements the schema can be defined in case you want to enable specific operations or you can use plone.behavior.AnnotationStorage as the default annotation storage.

For example in case you want to have a class that stores the field on the content and not on annotations:

```python
from plone.server.behaviors.properties import ContextProperty
from plone.server.behaviors.intrance import AnnotationBehavior
from zope.component import adapter
from plone.server.interfaces import IResource

@implementer(IMyLovedBehavior)
@adapter(IResource)
class MyBehavior(AnnotationBehavior):
    """If attributes
    """
    text = ContextProperty(u'attribute', ())
```

On this example text will be stored on the context object and text2 as a annotation.

Once you have the schema, marker interface and the factory you can register on zcml:

```xml
      <plone:behavior
          title="Attachment"
          provides=".mybehavior.IMyLovedBehavior"
          marker=".mybehavior.IMarkerBehavior"
          factory=".mybehavior.MyBehavior"
          for="plone.server.interfaces.IResource"
          />

```


## Static behaviors

With behaviors you can define them as static for specific content types:

```xml
    <plone:contenttype
          portal_type="Item"
          schema=".content.IItem"
          class=".content.Item"
          behaviors=".behaviors.dublincore.IDublinCore"
        />
```

### Create and modify content with behaviors

On the deserialization of the content you will need to pass on the POST/PATCH operation the behavior as a object on the JSON.


CREATE an ITEM with the expires : POST on parent:

```json
    {
        "@type": "Item",
        "plone.server.behaviors.dublincore.IDublinCore": {
            "expires": "1/10/2017"
        }
    }
```

MODIFY an ITEM with the expires : PATCH on the object:

```json
    {
        "plone.server.behaviors.dublincore.IDublinCore": {
            "expires": "1/10/2017"
        }
    }
```

### Get content with behaviors

On the serialization of the content you will get the behaviors as objects on the content.

GET an ITEM : GET on the object:

```json
    {
        "@id": "http://localhost:8080/zodb/plone/item1",
        "plone.server.behaviors.dublincore.IDublinCore": {
            "expires": "2017-10-01T00:00:00.000000+00:00",
            "modified": "2016-12-02T14:14:49.859953+00:00",
        }
    }
```


## Dynamic Behaviors

plone.server offers the option to have content that has dynamic behaviors applied to them.

### Which behaviors are available on a context

We can know which behaviors can be applied to a specific content.

GET CONTENT_URI/@behaviors:

```json

    {
        "available": ["plone.server.behaviors.attachment.IAttachment"],
        "static": ["plone.server.behaviors.dublincore.IDublinCore"],
        "dynamic": [],
        "plone.server.behaviors.attachment.IAttachment": { },
        "plone.server.behaviors.dublincore.IDublinCore": { }
    }
```

This list of behaviors is based on the for statement on the zcml definition of the behavior. The list on static are the ones defined on the content type definition on the zcml. The list on dynamic are the ones that have been assigned.

### Add a new behavior to a content

We can add a new dynamic behavior to a content by a PATCH operation on the object with the @behavior attribute or in a small PATCH operation to @behavior entry point with the value to add.

MODIFY an ITEM with the expires : PATCH on the object:

```json

    {
        "plone.server.behaviors.dublincore.IDublinCore": {
            "expires": "1/10/2017"
        }
    }
```

MODIFY behaviors : PATCH on the object/@behaviors:

```json
    {
        "behavior": "plone.server.behaviors.dublincore.IDublinCore"
    }
```

### Delete a behavior to a content

We can add a new dynamic behavior to a content by a DELETE operation to @behavior entry point with the value to remove.

DELETE behaviors : DELETE on the object/@behaviors:

```json
    {
        "behavior": "plone.server.behaviors.dublincore.IDublinCore"
    }
```

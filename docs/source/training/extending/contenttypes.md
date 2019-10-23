# Content types

For chatting, we'll need a content type for conversations and messages.

Create a `content.py` file in your application and create the content types.

```python
from guillotina import configure, content, schema
from guillotina.directives import index_field
from guillotina.interfaces import IFolder, IItem


class IConversation(IFolder):

    index_field("users", type="keyword")
    users = schema.List(
        value_type=schema.TextLine(),
        default=list()
    )


@configure.contenttype(
    type_name="Conversation",
    schema=IConversation,
    behaviors=["guillotina.behaviors.dublincore.IDublinCore"],
    allowed_types=['Message'])
class Conversation(content.Folder):
    pass


class IMessage(IItem):
    index_field("text", type="text")
    text = schema.Text(required=True)


@configure.contenttype(
    type_name="Message",
    schema=IMessage,
    behaviors=[
        "guillotina.behaviors.dublincore.IDublinCore",
        "guillotina.behaviors.attachment.IAttachment"
    ])
class Message(content.Item):
    pass
```

The `index_field` exposes those fields to be searched by with the `@search` endpoint.

In order for Guillotina to detect your configuration, you'll need to add
a scan call inside your `includeme` function in the `__init__.py` file.


```python
from guillotina import configure
configure.scan('guillotina_chat.content')
```


## Test it out

Using Postman test your new content types. First create a Conversation, then create a Message inside of it.

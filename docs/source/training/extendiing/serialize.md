# Serialize content

Guillotina provides default serializations for content. It provides mechanisms
for giving full content serialization of interfaces and behaviors as well as
summary serializations that show in listings.

For customize a serialization for a type, you need to provide a multi adapter
for the `IResourceSerializeToJsonSummary` or `IResourceSerializeToJson` interfaces.

For our use-case, we want to make sure to include the `creation_date` in the
summary serialization of conversations and messages.


# Defining a custom serialization

Let's define these serializers in a in a file named `serialize.py`.

```python
from guillotina import configure
from guillotina.interfaces import IResourceSerializeToJsonSummary
from guillotina.json.serialize_content import DefaultJSONSummarySerializer
from guillotina_chat.content import IConversation, IMessage
from zope.interface import Interface


@configure.adapter(
    for_=(IConversation, Interface),
    provides=IResourceSerializeToJsonSummary)
class ConversationJSONSummarySerializer(DefaultJSONSummarySerializer):
    async def __call__(self):
        data = await super().__call__()
        data['creation_date'] = self.context.creation_date
        return data


@configure.adapter(
    for_=(IMessage, Interface),
    provides=IResourceSerializeToJsonSummary)
class MessageJSONSummarySerializer(ConversationJSONSummarySerializer):
    async def __call__(self):
        data = await super().__call__()
        data['text'] = self.context.text
        return data
```

And make sure to add the scan.

```python
configure.scan('guillotina_chat.serialize')
```

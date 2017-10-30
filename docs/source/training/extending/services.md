# Services

Services are synonymous with what other frameworks might call `endpoints` or `views`.

For the sake of our application, let's use services for getting a user's most
recent conversations and messages for a conversation.


## Creating the services

We'll name our endpoints `@get-conversations` and `@get-messages` and put them
in a file named `services.py`.

```python
from guillotina import configure
from guillotina.component import get_multi_adapter
from guillotina.interfaces import IContainer, IResourceSerializeToJsonSummary
from guillotina.utils import get_authenticated_user_id
from guillotina_chat.content import IConversation


@configure.service(for_=IContainer, name='@get-conversations',
                   permission='guillotina.Authenticated')
async def get_conversations(context, request):
    results = []
    conversations = await context.async_get('conversations')
    user_id = get_authenticated_user_id(request)
    async for conversation in conversations.async_values():
        if user_id in getattr(conversation, 'users', []):
            summary = await get_multi_adapter(
                (conversation, request),
                IResourceSerializeToJsonSummary)()
            results.append(summary)
    results = sorted(results, key=lambda conv: conv['creation_date'])
    return results


@configure.service(for_=IConversation, name='@get-messages',
                   permission='guillotina.AccessContent')
async def get_messages(context, request):
    results = []
    async for message in context.async_values():
        summary = await get_multi_adapter(
            (message, request),
            IResourceSerializeToJsonSummary)()
        results.append(summary)
    results = sorted(results, key=lambda mes: mes['creation_date'])
    return results
```

And make sure to add the scan.

```python
configure.scan('guillotina_chat.services')
```

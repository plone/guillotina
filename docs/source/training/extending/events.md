# Event subscribers

Events in Guillotina are heavily influenced from zope events with the caveat
in that we support async event handlers.

For our chat application, we want to make sure every user that is part of a
conversation has permission to add new messages and view other messages.

A simple way to do this is with an event handler that modifies permissions.

A an `subscribers.py` file inside your application.


```python
from guillotina import configure
from guillotina.interfaces import IObjectAddedEvent, IPrincipalRoleManager
from guillotina.utils import get_authenticated_user_id, get_current_request
from guillotina_chat.content import IConversation


@configure.subscriber(for_=(IConversation, IObjectAddedEvent))
async def container_added(conversation, event):
    user_id = get_authenticated_user_id(get_current_request())
    if user_id not in conversation.users:
        conversation.users.append(user_id)

    manager = IPrincipalRoleManager(conversation)
    for user in conversation.users:
        manager.assign_role_to_principal(
            'guillotina_chat.ConversationParticipant', user)
```


In order for Guillotina to detect your configuration, you'll need to add
a scan call inside your `includeme` function in the `__init__.py` file.


```python
from guillotina import configure
configure.scan('guillotina_chat.subscribers')
```


## Test it out

Using Postman, add a Conversation and then a Message to that conversation
and then use the `@sharing` endpoint to inspect the assigned permissions.

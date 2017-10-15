# Permissions/Role

Permissions are defined in your application code.

For our app, we'll create roles that users are granted inside a conversation.

Add the following inside your `__init__.py` file.

```python
configure.role("guillotina_chat.ConversationParticipant",
               "Conversation Participant",
               "Users that are part of a conversation", False)
configure.grant(
    permission="guillotina.ViewContent",
    role="guillotina_chat.ConversationParticipant")
configure.grant(
    permission="guillotina.AccessContent",
    role="guillotina_chat.ConversationParticipant")
configure.grant(
    permission="guillotina.AddContent",
    role="guillotina_chat.ConversationParticipant")
```

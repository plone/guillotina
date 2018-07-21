# Events

Guillotina provides an event/subscriber pattern for dispatching
events out to subscribers when "things" happen in Guillotina.

## Subscribing

Subscribing to events is done with the `configure` module.

All subscribers are configured with:

 1. the object type to match subcribe to the event against
 2. the type of event you want to subscribe to


For example, to subscribe when an object is modified:

```python
from guillotina import configure
from guillotina.interfaces import IResource
from guillotina.interfaces import IObjectModifiedEvent

@configure.subscriber(for_=(IResource, IObjectModifiedEvent))
async def modified_object(obj, event):
    pass
```

## Creating events

You are also able to create your own events to notify on:

```python
from guillotina.interfaces import IObjectEvent
from zope.interface import implementer
from guillotina.event import notify

class ICustomEvent(IObjectEvent):
    pass

@implementer(IObjectEvent)
class CustomEvent:

    def __init__(self, object):
        self.object = object


await notify(CustomEvent(ob))
```

## Events

- guillotina.interfaces.IObjectEvent: every time anything happens to an object
- guillotina.interfaces.IFileStartedUpload
- guillotina.interfaces.IFileFinishUploaded
- guillotina.interfaces.IFileBeforeFinishUploaded
- guillotina.interfaces.IObjectLocationEvent: Base event for remove/rename
- guillotina.interfaces.IObjectMovedEvent
- guillotina.interfaces.IBeforeObjectMovedEvent
- guillotina.interfaces.IObjectAddedEvent: when content added to folder
- guillotina.interfaces.IObjectDuplicatedEvent
- guillotina.interfaces.IBeforeObjectAddedEvent
- guillotina.interfaces.IObjectRemovedEvent
- guillotina.interfaces.IBeforeObjectRemovedEvent
- guillotina.interfaces.IObjectModifiedEvent
- guillotina.interfaces.IObjectPermissionsModifiedEvent
- guillotina.interfaces.INewUserAdded

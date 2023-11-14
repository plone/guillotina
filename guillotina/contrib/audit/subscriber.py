from guillotina import configure
from guillotina.component import query_utility
from guillotina.contrib.audit.interfaces import IAuditUtility
from guillotina.interfaces import IObjectAddedEvent
from guillotina.interfaces import IObjectModifiedEvent
from guillotina.interfaces import IObjectRemovedEvent
from guillotina.interfaces import IResource


@configure.subscriber(for_=(IResource, IObjectAddedEvent), priority=1001)  # after indexing
async def audit_object_added(obj, event):
    audit = query_utility(IAuditUtility)
    audit.log_entry(obj, event)


@configure.subscriber(for_=(IResource, IObjectModifiedEvent), priority=1001)  # after indexing
async def audit_object_modified(obj, event):
    audit = query_utility(IAuditUtility)
    audit.log_entry(obj, event)


@configure.subscriber(for_=(IResource, IObjectRemovedEvent), priority=1001)  # after indexing
async def audit_object_removed(obj, event):
    audit = query_utility(IAuditUtility)
    audit.log_entry(obj, event)

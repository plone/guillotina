from guillotina.contrib.workflows.interfaces import IWorkflowChangedEvent
from guillotina.events import ObjectEvent
from zope.interface import implementer


@implementer(IWorkflowChangedEvent)
class WorkflowChangedEvent(ObjectEvent):
    """An object has been moved"""

    def __init__(self, object, workflow, action, comments):
        ObjectEvent.__init__(self, object)
        self.object = object
        self.workflow = workflow
        self.action = action
        self.comments = comments

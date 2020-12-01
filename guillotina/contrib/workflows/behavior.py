from guillotina import configure
from guillotina.behaviors.instance import ContextBehavior
from guillotina.contrib.workflows.interfaces import IWorkflowBehavior


@configure.behavior(
    title="Workflow data behavior", provides=IWorkflowBehavior, for_="guillotina.interfaces.IResource"
)
class WorkflowBehavior(ContextBehavior):
    auto_serialize = True

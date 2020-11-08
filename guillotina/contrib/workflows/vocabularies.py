from guillotina import configure
from guillotina.component import get_utility
from guillotina.contrib.workflows.interfaces import IWorkflow
from guillotina.contrib.workflows.interfaces import IWorkflowUtility
from guillotina.interfaces import IResource


@configure.vocabulary(name="worklow_states")
class WorkflowVocabulary:
    def __init__(self, context):
        self.context = context
        self.utility = get_utility(IWorkflowUtility)
        if not IResource.providedBy(context):
            self.states = IWorkflow(context.context).states
        else:
            self.states = IWorkflow(context).states

    def keys(self):
        return self.states

    def __iter__(self):
        return iter([x for x in self.states.keys()])

    def __contains__(self, value):
        return value in self.states

    def __len__(self):
        return len(self.states)

    def getTerm(self, value):
        if value in self.states:
            return value
        else:
            raise KeyError("No valid state")

from guillotina import configure
from guillotina.component import query_adapter
from guillotina.contrib.workflows.interfaces import IWorkflow
from guillotina.contrib.workflows.interfaces import IWorkflowBehavior
from guillotina.interfaces import IObjectAddedEvent
from guillotina.interfaces import IResource
from guillotina.security.utils import apply_sharing
from guillotina.utils import get_authenticated_user_id

import datetime


@configure.subscriber(for_=(IResource, IObjectAddedEvent), priority=1001)  # after indexing
async def workflow_object_added(obj, event):
    workflow = query_adapter(obj, IWorkflowBehavior)
    wkf = query_adapter(obj, IWorkflow)
    if workflow is not None and wkf is not None:
        user_id = get_authenticated_user_id()

        await workflow.load(create=True)
        state = workflow.review_state

        if "set_permission" in wkf.states[state]:
            await apply_sharing(obj, wkf.states[state]["set_permission"])

        setattr(workflow, "history", [])
        workflow.history.append(
            {
                "actor": user_id,
                "comments": "",
                "time": datetime.datetime.now(),
                "title": "Created",
                "type": "workflow",
                "data": {"action": None, "review_state": state},
            }
        )
        workflow.register()

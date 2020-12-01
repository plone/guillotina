from guillotina import configure
from guillotina.api.service import Service
from guillotina.component import query_adapter
from guillotina.contrib.workflows.interfaces import IWorkflow
from guillotina.contrib.workflows.interfaces import IWorkflowBehavior
from guillotina.interfaces import IAbsoluteURL
from guillotina.interfaces import IResource


class Workflow(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request


@configure.service(
    context=IResource,
    method="GET",
    permission="guillotina.AccessContent",
    name="@workflow",
    summary="Workflows for a resource",
    responses={"200": {"description": "Result results on workflows", "schema": {"properties": {}}}},
)
class WorkflowGET(Service):
    async def __call__(self):
        obj_url = IAbsoluteURL(self.context, self.request)()

        workflow = {"@id": obj_url + "/@workflow", "history": [], "transitions": []}

        workflow_obj = IWorkflow(self.context)
        if workflow_obj is None:
            return workflow
        async for action_name, action in workflow_obj.available_actions(self.request):
            workflow["transitions"].append(
                {"@id": obj_url + "/@workflow/" + action_name, "title": action["title"]}
            )

        workflow_obj = query_adapter(self.context, IWorkflowBehavior)
        if workflow_obj is not None:
            await workflow_obj.load()
            workflow["history"] = workflow_obj.history

        return workflow


@configure.service(
    context=IResource,
    method="POST",
    permission="guillotina.AccessContent",
    name="@workflow/{action_id}",
    summary="Components for a resource",
    responses={"200": {"description": "Change action of a workflow", "schema": {"properties": {}}}},
)
class DoAction(Service):
    async def __call__(self):
        action_id = self.request.matchdict["action_id"]
        comment = ""
        workflow = IWorkflow(self.context)
        result = await workflow.do_action(action_id, comment)
        return result

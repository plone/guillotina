from guillotina import app_settings
from guillotina import configure
from guillotina.component import provide_adapter
from guillotina.component import query_adapter
from guillotina.contrib.workflows import logger
from guillotina.contrib.workflows.events import WorkflowChangedEvent
from guillotina.contrib.workflows.interfaces import IWorkflow
from guillotina.contrib.workflows.interfaces import IWorkflowBehavior
from guillotina.contrib.workflows.interfaces import IWorkflowUtility
from guillotina.event import notify
from guillotina.events import ObjectModifiedEvent
from guillotina.response import HTTPPreconditionFailed
from guillotina.response import HTTPUnauthorized
from guillotina.security.utils import apply_sharing
from guillotina.utils import get_authenticated_user_id
from guillotina.utils import get_security_policy
from guillotina.utils import import_class

import datetime


def create_workflow_factory(proto_name, proto_definition):
    class Workflow:

        name = proto_name
        definition = proto_definition

        def __init__(self, context):
            self.context = context
            self._states = self.definition["states"]
            self._initial_state = self.definition["initial_state"]

        @property
        def states(self):
            return self._states

        @property
        def actions(self):
            adapter = query_adapter(self.context, IWorkflowBehavior)
            if adapter is None:
                return {}
            state = adapter.review_state
            return self._states[state]["actions"]

        async def available_actions(self, request):
            policy = get_security_policy()
            for action_name, action in self.actions.items():
                add = False
                if "check_permission" in action and policy.check_permission(
                    action["check_permission"], self.context
                ):
                    add = True
                elif "check_permission" not in action:
                    add = True

                if add:
                    yield action_name, action

        @property
        def initial_state(self):
            return self._initial_state

        async def do_action(self, action, comments, bypass_permission_check=False):
            available_actions = self.actions
            if action not in available_actions:
                raise HTTPPreconditionFailed(content={"reason": "Unavailable action"})

            action_def = available_actions[action]
            if bypass_permission_check is False:
                policy = get_security_policy()
                if "check_permission" in action_def and not policy.check_permission(
                    action_def["check_permission"], self.context
                ):
                    raise HTTPUnauthorized()

            # Change permission
            new_state = action_def["to"]

            if "set_permission" in self.states[new_state]:
                await apply_sharing(self.context, self.states[new_state]["set_permission"])

            # Write history
            user = get_authenticated_user_id()
            history = {
                "actor": user,
                "comments": comments,
                "time": datetime.datetime.now(),
                "title": action_def["title"],
                "type": "workflow",
                "data": {"action": action, "review_state": new_state},
            }

            workflow_behavior = IWorkflowBehavior(self.context)
            workflow_behavior.review_state = new_state

            workflow_behavior.history.append(history)
            workflow_behavior.register()

            await notify(WorkflowChangedEvent(self.context, self, action, comments))
            await notify(ObjectModifiedEvent(self.context, payload={"review_state": new_state}))
            return history

    return Workflow


@configure.utility(provides=IWorkflowUtility)
class WorkflowUtility:

    index_count = 0

    def __init__(self, settings={}):
        self.workflows = app_settings["workflows"]
        self.workflows_content = app_settings["workflows_content"]
        self.factories = {}

    async def initialize(self, app):
        self.app = app
        for workflow_name, definition in self.workflows.items():
            logger.info(f"Registered workflow {workflow_name}")
            factory = create_workflow_factory(workflow_name, definition)
            self.factories[workflow_name] = factory
        for interface_str, workflow in self.workflows_content.items():
            logger.info(f"Linked workflow {workflow} to {interface_str}")
            iface = import_class(interface_str)
            provide_adapter(self.factories[workflow], adapts=(iface,), provides=IWorkflow)

    async def finalize(self, app):
        self.factories = {}

    def states(self, context):
        return IWorkflow(context).states

    async def switch_state(self, context, action):
        await IWorkflow(context).switch_state(action)

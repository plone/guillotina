from guillotina import schema
from guillotina.component import query_adapter
from guillotina.directives import index_field
from guillotina.interfaces import IAsyncUtility
from guillotina.interfaces import IResource
from guillotina.schema.interfaces import IContextAwareDefaultFactory
from typing import Optional
from zope.interface import Attribute
from zope.interface import implementer
from zope.interface import Interface
from zope.interface import interfaces

import json


HISTORY_SCHEMA = json.dumps(
    {
        "type": "object",
        "properties": {
            "actor": {"type": "string"},
            "comments": {"type": "string"},
            "time": {"type": "string"},
            "type": {"type": "string"},
            "title": {"type": "string"},
            "data": {"type": "object", "properties": {}},
        },
    }
)


class IWorkflowUtility(IAsyncUtility):
    pass


class IWorkflow(Interface):

    initial_state = Attribute("Initial state of the workflow")


class IWorkflowChangedEvent(interfaces.IObjectEvent):
    """An object workflow has been modified"""


@implementer(IContextAwareDefaultFactory)
class DefaultReviewState:
    def __call__(self, context: IResource) -> Optional[str]:
        if context is None:
            return None
        workflow = query_adapter(context.context, IWorkflow)
        if workflow is not None:
            return workflow.initial_state
        else:
            return None


class IWorkflowBehavior(Interface):

    index_field("review_state", store=True, type="keyword")
    review_state = schema.Choice(
        readonly=True,
        title="Workflow review state",
        required=False,
        defaultFactory=DefaultReviewState(),
        source="worklow_states",
    )

    history = schema.List(
        title="History list",
        readonly=True,
        required=False,
        defaultFactory=list,
        value_type=schema.JSONField(title="History element", schema=HISTORY_SCHEMA),
    )

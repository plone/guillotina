from guillotina.interfaces import IAsyncUtility
from guillotina.schema.interfaces import IContextAwareDefaultFactory
from guillotina.interfaces import IResource
from zope.interface import Interface
from zope.interface import interfaces
from zope.interface import implementer
from guillotina import schema
from guillotina.directives import index_field
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
    pass


class IWorkflowChangedEvent(interfaces.IObjectEvent):
    """An object workflow has been modified"""


@implementer(IContextAwareDefaultFactory)
class DefaultReviewState:
    def __call__(self, context: IResource = None) -> str:
        return IWorkflow(context.context).initial_state


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

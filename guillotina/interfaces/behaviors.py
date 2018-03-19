from guillotina import schema
from zope.interface import Attribute
from zope.interface import Interface
from zope.interface.interfaces import IInterface


class IBehavior(Interface):
    """A description of a behavior. These should be registered as named
    utilities. There should also be an adapter factory registered, probably
    using IBehaviorAdapterFactory.
    """

    title = schema.TextLine(
        title=u'Short title of the behavior',
        required=True
    )

    description = schema.Text(
        title=u'Longer description of the behavior',
        required=False
    )

    name = schema.TextLine(
        title=u'Readable short name to be used for behavior lookup',
        description=u'E.g. plone.somebehavior. If not given the full dotted '
                    u'name of the interfaces is used for lookup instead.'
                    u'Recommended, but due to BBB not required.',
        required=False
    )

    interface = schema.Object(
        title=u'Interface describing this behavior',
        required=True,
        schema=IInterface
    )

    marker = schema.Object(
        title=u'Marker interface for objects sporting this behavior',
        description=u'Markers are persisted in the database. '
                    u'Required when a factory is given, because the factory '
                    u'is an adapter adapting the the marker and providing the '
                    u'"interface" of this behavior.',
        required=False,
        schema=IInterface
    )

    factory = schema.Object(
        title=u'An adapter factory for the behavior',
        required=True,
        schema=Interface
    )


class IBehaviorSchemaAwareFactory(Interface):
    """Marker interface for factories that should be initialised with a
    schema. The factory must be a callable that takes the schema as an
    argument and returns another callable that can create appropriate behavior
    factories on demand.

    See annotation.py for an example.
    """


class IBehaviorAdapterFactory(Interface):
    """An adapter factory that wraps a given behavior's own factory. By
    registering an adapter from Interface (or some other general source) to
    the behavior's interface that uses this factory, we can easily support
    the following semantics:

        context = SomeObject()
        behavior_adapter = ISomeBehavior(context, None)

    """

    behavior = schema.Object(
        title='The behavior this is a factory for',
        schema=IBehavior
    )

    def __call__(context):  # noqa: N805
        """
        Invoke the behavior-specific factory if the context can be adapted
        """


class IContentBehavior(Interface):
    '''
    '''
    auto_serialize = Attribute('Automatically serialize behavior')


class IAsyncBehavior(IContentBehavior):
    """
    A behavior that needs to load initial data asynchronously.
    In order for data api to work correctly, `await behavior.load()` will
    need to be called first.
    """
    def load(create=False):  # noqa: N805
        '''
        load data for a behavior
        '''

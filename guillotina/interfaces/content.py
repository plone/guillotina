# NEED use this import because we have a "schema" attribute below
from guillotina.component.interfaces import ISite as IComponentSite
from guillotina.component.interfaces import IFactory
from guillotina.interfaces.common import IMapping
from guillotina.schema import TextLine
from zope.interface import Attribute
from zope.interface import Interface

# NEED use this import because we have a "schema" attribute below
import guillotina.schema


class IAsyncContainer(Interface):
    """
    object that supports getting and setting sub-objects
    asynchronously
    """

    async def async_get(name, default=None, suppress_events=False):  # noqa: N805
        """
        asynchronously get subobject
        """

    async def async_set(name, value):  # noqa: N805
        """
        asynchronously get subobject
        """

    async def async_keys():  # type: ignore
        """
        asynchronously get keys for sub objects
        """

    async def async_del(name):  # noqa: N805
        """
        asynchronously delete sub object
        """

    async def async_items():  # type: ignore
        """
        asynchronously get items
        """

    async def async_len():  # type: ignore
        """
        asynchronously get len
        """

    async def async_contains(name):  # noqa: N805
        """
        asynchronously check if contains
        """


class IRegistry(IMapping):

    def for_interface(interface, check=True, omit=(), prefix=None):  # noqa: N805
        """Get an IRecordsProxy for the given interface. If `check` is True,
        an error will be raised if one or more fields in the interface does
        not have an equivalent setting.
        """

    def register_interface(interface, omit=(), prefix=None):  # noqa: N805
        """Create a set of records based on the given interface. For each
        schema field in the interface, a record will be inserted with a
        name like `${interface.__identifier__}.${field.__name__}`, and a
        value equal to default value of that field. Any field with a name
        listed in `omit`, or with the `readonly` property set to True, will
        be ignored. Supply an alternative identifier with `prefix`.
        """


class ITraversable(Interface):
    """
    A content object that contains content that can be traversed to
    """

    def get(name):  # noqa: N805
        '''
        '''


class IApplication(ITraversable, IAsyncContainer):
    '''
    '''


class IDatabase(ITraversable, IAsyncContainer):
    def get_transaction_manager():  # type: ignore
        '''
        '''

    def open():  # type: ignore
        '''
        '''


class IStaticFile(Interface):
    '''
    '''


class IStaticDirectory(ITraversable):
    '''
    '''


class IJavaScriptApplication(IStaticDirectory):
    '''
    '''


class ILocation(Interface):
    """Objects that can be located in a hierachy.

    Given a parent and a name an object can be located within that parent. The
    locatable object's `__name__` and `__parent__` attributes store this
    information.

    Located objects form a hierarchy that can be used to build file-system-like
    structures. For example in Zope `ILocation` is used to build URLs and to
    support security machinery.

    To retrieve an object from its parent using its name, the `ISublocation`
    interface provides the `sublocations` method to iterate over all objects
    located within the parent. The object searched for can be found by reading
    each sublocation's __name__ attribute.

    """

    __parent__ = Attribute('The parent in the location hierarchy.')

    __name__ = TextLine(
        title='The name within the parent',
        description="The object can be looked up from the parent's "
                    'sublocations using this name.',
        required=False,
        default=None,
        readonly=True)


class IResource(ILocation):

    type_name = guillotina.schema.TextLine(readonly=True)

    title = guillotina.schema.TextLine(
        title='Title',
        required=False,
        description=u'Title of the Resource',
        default=u''
    )

    uuid = guillotina.schema.TextLine(
        title='UUID',
        required=True,
        readonly=True
    )

    modification_date = guillotina.schema.Datetime(
        title='Modification date',
        required=False
    )

    creation_date = guillotina.schema.Datetime(
        title='Creation date',
        required=False
    )

    __behaviors__ = guillotina.schema.FrozenSet(
        title='Enabled behaviors',
        required=False,
        description='Dynamic behaviors for the content type',
        default=frozenset({}),
        readonly=True
    )


class IResourceFactory(IFactory):

    type_name = guillotina.schema.TextLine(
        title='Portal type name',
        description='The portal type this is an FTI for'
    )

    schema = guillotina.schema.DottedName(
        title='Schema interface',
        description='Dotted name to an interface describing the type. '
                    'This is not required if there is a model file or a '
                    'model source string containing an unnamed schema.'
    )

    behaviors = guillotina.schema.List(
        title='Behaviors',
        description='A list of behaviors that are enabled for this type. '
                    'See guillotina.behaviors for more details.',
        value_type=guillotina.schema.DottedName(title='Behavior name')
    )

    add_permission = guillotina.schema.DottedName(
        title='Add permission',
        description='A oermission name for the permission required to '
                    'construct this content',
    )


class IFolder(IResource, IAsyncContainer, ITraversable):
    '''
    '''


class IContainer(IResource, IAsyncContainer, ITraversable, IComponentSite):
    '''
    Formally known as ISite.
    This is a base container to hold content.
    A database can hold multiple containers
    '''


class IItem(IResource):
    '''
    '''


class IAnnotations(Interface):
    '''
    '''


class IAnnotationData(Interface):
    '''
    '''


class IGroupFolder(IFolder):
    '''
    Group content.
    Main purpose of this PR is to prevent reindexing on modify permissions
    for group content.
    '''


class IGetOwner(Interface):
    '''
    Defines a utility for calculating the owner of a new resource
    '''


class IIDGenerator(Interface):
    '''
    Generates an id on a POST for the new object
    '''

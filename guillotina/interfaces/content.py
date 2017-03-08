# NEED use this import because we have a "schema" attribute below
from guillotina.interfaces.common import IMapping
from zope.component.interfaces import ISite as IZopeSite
from zope.component.interfaces import IFactory
from zope.interface import Attribute
from zope.interface import Interface
from guillotina.schema import TextLine

# NEED use this import because we have a "schema" attribute below
import guillotina.schema


class IRegistry(IMapping):

    def for_interface(interface, check=True, omit=(), prefix=None):
        """Get an IRecordsProxy for the given interface. If `check` is True,
        an error will be raised if one or more fields in the interface does
        not have an equivalent setting.
        """

    def register_interface(interface, omit=(), prefix=None):
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

    def get(name):
        pass


class IApplication(ITraversable):
    pass


class IDatabase(ITraversable):
    def get_transaction_manager():
        pass

    def open():
        pass


class IStaticFile(Interface):
    pass


class IStaticDirectory(Interface):
    pass


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

    __parent__ = Attribute("The parent in the location hierarchy.")

    __name__ = TextLine(
        title=u"The name within the parent",
        description="The object can be looked up from the parent's "
                    "sublocations using this name.",
        required=False,
        default=None)


class IResource(ILocation):

    portal_type = guillotina.schema.TextLine()

    title = guillotina.schema.TextLine(
        title='Title',
        required=False,
        description=u'Title of the Resource',
        default=u''
    )

    __behaviors__ = guillotina.schema.FrozenSet(
        title='Enabled behaviors',
        required=False,
        description=u'Dynamic behaviors for the content type',
        default=frozenset({})
    )


class IResourceFactory(IFactory):

    portal_type = guillotina.schema.TextLine(
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


class ISite(IResource, IZopeSite, ITraversable):
    pass


class IItem(IResource):
    pass


class IContainer(IResource, IMapping, ITraversable):
    pass


class IContentNegotiation(Interface):
    pass


class IAnnotations(Interface):
    pass

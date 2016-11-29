from zope.component.interfaces import ISite as IZopeSite
from zope.component.interfaces import IFactory
from zope.interface import Interface
from zope.interface.common.mapping import IFullMapping
from zope.location.interfaces import IContained

# NEED use this import because we have a "schema" attribute below
import zope.schema


class IRegistry(IFullMapping):

    def forInterface(interface, check=True, omit=(), prefix=None):
        """Get an IRecordsProxy for the given interface. If `check` is True,
        an error will be raised if one or more fields in the interface does
        not have an equivalent setting.
        """

    def registerInterface(interface, omit=(), prefix=None):
        """Create a set of records based on the given interface. For each
        schema field in the interface, a record will be inserted with a
        name like `${interface.__identifier__}.${field.__name__}`, and a
        value equal to default value of that field. Any field with a name
        listed in `omit`, or with the `readonly` property set to True, will
        be ignored. Supply an alternative identifier with `prefix`.
        """


class IApplication(Interface):
    pass


class IDataBase(Interface):
    pass


class IStaticFile(Interface):
    pass


class IStaticDirectory(Interface):
    pass


class IResource(IContained):
    portal_type = zope.schema.TextLine()

    title = zope.schema.TextLine(
        title='Title',
        required=False,
        description=u"Title of the Resource",
        default=u''
    )


class IResourceFactory(IFactory):

    portal_type = zope.schema.TextLine(
        title='Portal type name',
        description='The portal type this is an FTI for'
    )

    schema = zope.schema.DottedName(
        title='Schema interface',
        description='Dotted name to an interface describing the type. '
                    'This is not required if there is a model file or a '
                    'model source string containing an unnamed schema.'
    )

    behaviors = zope.schema.List(
        title='Behaviors',
        description='A list of behaviors that are enabled for this type. '
                    'See plone.behavior for more details.',
        value_type=zope.schema.DottedName(title='Behavior name')
    )

    add_permission = zope.schema.DottedName(
        title='Add permission',
        description='A oermission name for the permission required to '
                    'construct this content',
    )


class ISite(IResource, IZopeSite):
    pass


class IItem(IResource):
    pass


class IContainer(IResource, IFullMapping):
    pass


class IContentNegotiation(Interface):
    pass

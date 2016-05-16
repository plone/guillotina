from zope.interface import Interface
from zope.configuration import fields as configuration_fields
from plone.dexterity.fti import register
from plone.dexterity.fti import DexterityFTI


class IContentTypeDirective(Interface):

    portal_type = configuration_fields.MessageID(
        title=u"Portal type",
        description=u"",
        required=True)

    schema = configuration_fields.GlobalInterface(
        title=u"",
        description=u"",
        required=True)

    behaviors = configuration_fields.Tokens(
        title=u"",
        description=u"",
        value_type=configuration_fields.GlobalInterface(),
        required=True)


def contenttypeDirective(_context,
                         portal_type,
                         schema,
                         behaviors=[],
                         add_permission=None):
    """ Generate a Dexterity FTI and factory for the passed schema """
    interface_name = schema.__identifier__
    behavior_names = [a.__identifier__ for a in behaviors]

    fti_args = {'id': portal_type,
                'schema': interface_name,
                'behaviors': behavior_names}
    if add_permission is not None:
        fti_args['add_permission'] = add_permission

    fti = DexterityFTI(**fti_args)

    register(fti)

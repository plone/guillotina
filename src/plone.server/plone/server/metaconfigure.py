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


# -*- coding: utf-8 -*-
# from zope.configuration.exceptions import ConfigurationError
# from zope.configuration.fields import GlobalObject
from zope.interface import Interface
from zope.configuration.fields import Path
from zope.configuration.exceptions import ConfigurationError
import os
import json
import plone.server
import importlib
from zope.component.zcml import adapter
from plone.server.utils import import_class
from plone.server.interfaces import IView, IResponse, IRendered
from plone.dexterity.interfaces import IDexterityContent
from plone.server import DICT_RENDERS, DICT_METHODS, DICT_LANGUAGES, DEFAULT_LAYER, DEFAULT_PERMISSION
# from zope.schema import TextLine, Bool, Text
# from zope.publisher.interfaces.browser import IBrowserPublisher
# from plone.rest import interfaces
# from plone.rest.traverse import NAME_PREFIX
# from plone.rest.negotiation import register_service
# from plone.rest.cors import options_view, options_view_wrap, wrap_cors
from zope.security.checker import CheckerPublic, Checker, defineChecker
from zope.security.checker import getCheckerForInstancesOf, undefineChecker

# 
# from zope.security.zcml import Permission



class IApi(Interface):
    """
    """

    file = Path(
        title=u"The name of a file defining the api.",
        description=u"""
        Refers to a file containing a json definition.""",
        required=False
    )


def register_service(
        _context,
        configuration,
        content,
        method,
        layer,
        default_permission,
        name=''):
    print(configuration)
    factory = import_class(configuration['factory'])
    if factory is None:
        raise TypeError("Factory not defined %s " % configuration['factory'])
    if getCheckerForInstancesOf(factory):
        # in case already exist remove old checker
        undefineChecker(factory)
    if 'permission' in configuration:
        permission = configuration['permission']
    else:
        permission = default_permission
    required = {}
    for n in ('__call__', 'publishTraverse'):
        required[n] = permission

    defineChecker(factory, Checker(required))
    print("Defining adapter for %s %s %s to %s name %s" % (
        content,
        DICT_METHODS[method],
        layer,
        factory,
        name
        )
    )
    adapter(
        _context,
        factory=(factory,),
        provides=DICT_METHODS[method],
        for_=(content, layer),
        name=name
    )


def apiDirective(_context, file):

    if file:
        file = os.path.abspath(_context.path(file))
        if not os.path.isfile(file):
            raise ConfigurationError("No such file", file)

    with open(file, 'r') as f:
        json_info = json.loads(f.read())
        f.close()

    if 'methods' in json_info:
        for method, method_interface in json_info['methods'].items():
            DICT_METHODS[method] = import_class(method_interface)

    if 'layer' in json_info:
        layer = json_info['layer']
        layer = import_class(layer)
        if len(DEFAULT_LAYER) == 0:
            DEFAULT_LAYER.append(layer)
    else:
        layer = DEFAULT_LAYER[0]

    if 'default_permission' in json_info:
        default_permission = json_info['default_permission']
        if len(DEFAULT_PERMISSION) == 0:
            DEFAULT_PERMISSION.append(default_permission)
    else:
        default_permission = DEFAULT_PERMISSION[0]

    if 'renderers' in json_info:
        for accept, renderer_interface in json_info['renderers'].items():
            # We define which Interface is for the content negotiation
            DICT_RENDERS[accept] = import_class(renderer_interface)

    if 'languages' in json_info:
        for language, language_interface in json_info['languages'].items():
            # We define which Interface is for the languages
            print(language_interface)
            DICT_LANGUAGES[language] = import_class(language_interface)

    if 'contenttypes' in json_info:
        for contenttype, configuration in json_info['contenttypes'].items():
            content_interface = import_class(contenttype)
            for method, method_configuration in configuration.items():
                if method != 'endpoints':
                    register_service(
                        _context,
                        method_configuration,
                        content_interface,
                        method,
                        layer,
                        default_permission)

            if 'endpoints' in configuration:
                for endpoint, endpoint_configuration in configuration['endpoints'].items():
                    for method, method_configuration in endpoint_configuration.items():
                        register_service(
                            _context,
                            method_configuration,
                            content_interface,
                            method,
                            layer,
                            default_permission,
                            endpoint)




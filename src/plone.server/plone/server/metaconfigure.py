# -*- coding: utf-8 -*-
from collections import MutableMapping
from collections import OrderedDict
from functools import reduce
from pathlib import Path as osPath
from plone.server import _
from plone.server import AVAILABLE_ADDONS
from plone.server import DEFAULT_LAYER
from plone.server import DEFAULT_PERMISSION
from plone.server import DICT_LANGUAGES
from plone.server import DICT_METHODS
from plone.server import DICT_RENDERS
from plone.server.content import ResourceFactory
from plone.server.content import StaticDirectory
from plone.server.interfaces import DEFAULT_ADD_PERMISSION
from plone.server.interfaces import SCHEMA_CACHE
from plone.server.interfaces import IApplication
from plone.server.interfaces import IResourceFactory
from plone.server.security import ViewPermissionChecker
from plone.server.utils import import_class
from plone.behavior.interfaces import IBehavior
from zope.component import getUtility
from zope.component.zcml import adapter
from zope.component.zcml import utility
from zope.configuration import fields as configuration_fields
from zope.configuration.exceptions import ConfigurationError
from zope.configuration.fields import Path
from zope.interface import Interface
from zope.security.checker import defineChecker
from zope.security.checker import getCheckerForInstancesOf
from zope.security.checker import undefineChecker

import json
import logging
import os
import plone.server


logger = logging.getLogger(__name__)


def rec_merge(d1, d2):
    """
    Update two dicts of dicts recursively,
    if either mapping has leaves that are non-dicts,
    the second's leaf overwrites the first's.
    """
    # in Python 2, use .iteritems()!
    for k, v in d1.items():
        if k in d2:
            # this next check is the only difference!
            if all(isinstance(e, MutableMapping) for e in (v, d2[k])):
                d2[k] = rec_merge(v, d2[k])
            # we could further check types and merge as appropriate here.
    d3 = d1.copy()
    d3.update(d2)
    return d3


class IContentTypeDirective(Interface):

    portal_type = configuration_fields.MessageID(
        title=_('Portal type'),
        description='',
        required=True
    )

    class_ = configuration_fields.GlobalObject(
        title=_('Class'),
        description='',
        required=False
    )

    schema = configuration_fields.GlobalInterface(
        title='',
        description='',
        required=True
    )

    behaviors = configuration_fields.Tokens(
        title='',
        description='',
        value_type=configuration_fields.GlobalInterface(),
        required=False
    )

    allowed_types = configuration_fields.Tokens(
        title='',
        description='',
        value_type=configuration_fields.MessageID(),
        required=False
    )


def contenttypeDirective(_context,
                         portal_type,
                         class_,
                         schema,
                         behaviors=None,
                         add_permission=None,
                         allowed_types=None):
    """
    Generate factory for the passed schema
    """
    factory = ResourceFactory(
        class_,
        title='',
        description='',
        portal_type=portal_type,
        schema=schema,
        behaviors=behaviors or (),
        add_permission=add_permission or DEFAULT_ADD_PERMISSION,
        allowed_types=allowed_types
    )
    utility(
        _context,
        provides=IResourceFactory,
        component=factory,
        name=portal_type,
    )
    behaviors_registrations = []
    for iface in behaviors or ():
        if Interface.providedBy(iface):
            name = iface.__identifier__
        else:
            name = iface
        behaviors_registrations.append(getUtility(IBehavior, name=name))
    SCHEMA_CACHE[portal_type] = {
        'behaviors': behaviors_registrations,
        'schema': schema
    }


class IApi(Interface):

    file = Path(
        title='The name of a file defining the api.',
        description='Refers to a file containing a json definition.',
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
    logger.debug(configuration)
    factory = import_class(configuration['factory'])
    if factory is None:
        raise TypeError(
            'Factory not defined {0:s} '.format(configuration['factory']))
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

    defineChecker(factory, ViewPermissionChecker(required))
    logger.debug('Defining adapter for '  # noqa
                 '{0:s} {1:s} {2:s} to {3:s} name {4:s}'.format(
        content.__identifier__,
        DICT_METHODS[method].__identifier__,
        layer.__identifier__,
        str(factory),
        name))
    adapter(
        _context,
        factory=(factory,),
        provides=DICT_METHODS[method],
        for_=(content, layer),
        name=name
    )


def apiDirective(_context, file):  # noqa 'too complex' :)

    if file:
        file = os.path.abspath(_context.path(file))
        if not os.path.isfile(file):
            raise ConfigurationError('No such file', file)

    with open(file, 'r') as f:
        json_info = json.loads(f.read(), object_pairs_hook=OrderedDict)
        f.close()

    if 'contenttypes' in json_info:
        plone.server.JSON_API_DEFINITION = reduce(
            rec_merge,
            (json_info['contenttypes'], plone.server.JSON_API_DEFINITION))

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
            # Order is important !!
            DICT_RENDERS[accept] = import_class(renderer_interface)

    if 'languages' in json_info:
        for language, language_interface in json_info['languages'].items():
            # We define which Interface is for the languages
            logger.debug(language_interface)
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
                for endpoint, endpoint_configuration in configuration['endpoints'].items():  # noqa
                    for method, method_configuration in endpoint_configuration.items():  # noqa
                        register_service(
                            _context,
                            method_configuration,
                            content_interface,
                            method,
                            layer,
                            default_permission,
                            endpoint)


class IResourceDirectory(Interface):

    name = configuration_fields.MessageID(
        title=_('Name where is going to be published'),
        description='',
        required=True
    )

    directory = Path(
        title='The name of the directory',
        description='Publish at /static the directory',
        required=True
    )


def resourceDirectory(_context, name, directory):
    if directory:
        directory = osPath(_context.path(directory))
        if not directory.is_dir():
            raise ConfigurationError('No such directory', directory)
    root = getUtility(IApplication, 'root')
    if name not in root:
        root[name] = StaticDirectory(directory)


class IAddOn(Interface):

    name = configuration_fields.PythonIdentifier(
        title=_('Name of the addon'),
        description='',
        required=True
    )

    title = configuration_fields.MessageID(
        title=_('Name of the addon'),
        description='',
        required=True
    )

    handler = configuration_fields.GlobalObject(
        title=_('Handler for the addon'),
        description='',
        required=True
    )


def addOn(_context, name, title, handler):
    if name not in AVAILABLE_ADDONS:
        AVAILABLE_ADDONS[name] = {
            'title': title,
            'handler': handler
        }

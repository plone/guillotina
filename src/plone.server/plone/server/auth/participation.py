# -*- coding: utf-8 -*-
from zope.security.interfaces import IParticipation
from zope.interface import implementer
from zope.component import adapter
from plone.server.interfaces import IRequest
from collections import OrderedDict

# from AccessControl import ClassSecurityInfo
# from AccessControl.PermissionRole import _what_not_even_god_should_do
# from App.class_init import InitializeClass
# from App.special_dtml import DTMLFile
# from Products.PlonePAS.interfaces.plugins import ILocalRolesPlugin
# from Products.PlonePAS.interfaces.propertysheets import IMutablePropertySheet
# from Products.PluggableAuthService.PropertiedUser import PropertiedUser
# from Products.PluggableAuthService.UserPropertySheet import UserPropertySheet
# from Products.PluggableAuthService.interfaces.plugins import IPropertiesPlugin
# from Products.PluggableAuthService.interfaces.plugins import IUserFactoryPlugin
# from Products.PluggableAuthService.interfaces.propertysheets \
#     import IPropertySheet
# from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
# 
# from zope.interface import implementer
# from intranetum.horus.caller import call_horus
# from zope.globalrequest import getRequest
# import jwt
# import logging


class PloneUser(object):
    pass

#     def __init__(self, id, token, jwt_secret):
#         self._propertysheets = OrderedDict()

#         result = call_horus(plugin.horus_url, self._init_call, {
#             'service_token': plugin.service_token,
#             'user_token': token['token'],
#             'scope': plugin.scope,
#             'user': id
#         })
#         if not result:
#             raise KeyError('Not a Horus User')
#         user_data = jwt.decode(result.text, plugin.jwt_secret, algorithms=['HS256'])

#         self._init_data(user_data)

#     def _init_data(self, user_data):
#         self._roles = user_data['result']['roles']
#         self._groups = user_data['result']['groups']
#         self.name = user_data['result']['name']

#         if len(self._roles) == 0:
#             raise KeyError('Horus User has no roles in this Scope')      


#     def _getPAS(self):
#         # XXX This is not very optimal *at all*
#         return self.acl_users

#     def _getPlugins(self):
#         # XXX This is not very optimal *at all*
#         return self._getPAS().plugins

#     @security.public
#     def isGroup(self):
#         """Return 1 if this user is a group abstraction"""
#         return self._isGroup

#     @security.public
#     def getName(self):
#         """Get user's or group's name.
#         This is the id. PAS doesn't do prefixes and such like GRUF.
#         """
#         return self.name

#     @security.public
#     def getUserId(self):
#         """Get user's or group's name.
#         This is the id. PAS doesn't do prefixes and such like GRUF.
#         """
#         return self.getId()

#     @security.public
#     def getGroupNames(self):
#         """Return ids of this user's groups. GRUF compat."""
#         return self.getGroups()

#     security.declarePublic('getGroupIds')
#     getGroupIds = getGroupNames

#     #################################
#     # acquisition aware

#     @security.public
#     def getPropertysheet(self, id):
#         """ -> propertysheet (wrapped if supported)
#         """
#         sheet = self._propertysheets[id]
#         try:
#             return sheet.__of__(self)
#         except AttributeError:
#             return sheet

#     @security.private
#     def getRoles(self):
#         return self._roles

#     @security.private
#     def addPropertysheet(self, id, data):
#         """ -> add a prop sheet, given data which is either
#         a property sheet or a raw mapping.
#         """
#         if IPropertySheet.providedBy(data):
#             sheet = data
#         else:
#             sheet = UserPropertySheet(id, **data)

#         if self._propertysheets.get(id) is not None:
#             # In case is already there is a cached user on the same thread
#             return

#         self._propertysheets[id] = sheet

#     def _getPropertyPlugins(self):
#         return self._getPAS().plugins.listPlugins(IPropertiesPlugin)

#     @security.private
#     def getOrderedPropertySheets(self):
#         return self._propertysheets.values()

#     #################################
#     # local roles plugin type delegation

#     def _getLocalRolesPlugins(self):
#         return self._getPAS().plugins.listPlugins(ILocalRolesPlugin)

#     def getRolesInContext(self, object):
#         lrmanagers = self._getLocalRolesPlugins()
#         roles = set([])
#         # We change the order so we can remove specific role on context
#         roles.update(self.getRoles())
#         for lrid, lrmanager in lrmanagers:
#             roles.update(lrmanager.getRolesInContext(self, object))
#         return list(roles)

#     def allowed(self, object, object_roles=None):
#         if object_roles is _what_not_even_god_should_do:
#             return 0

#         # Short-circuit the common case of anonymous access.
#         if object_roles is None or 'Anonymous' in object_roles:
#             return 1

#         # Provide short-cut access if object is protected by 'Authenticated'
#         # role and user is not nobody
#         if 'Authenticated' in object_roles \
#            and self.getUserName() != 'Anonymous User':
#             return 1

#         # Check for ancient role data up front, convert if found.
#         # This should almost never happen, and should probably be
#         # deprecated at some point.
#         if 'Shared' in object_roles:
#             object_roles = self._shared_roles(object)
#             if object_roles is None or 'Anonymous' in object_roles:
#                 return 1

#         # Check for a role match with the normal roles given to
#         # the user, then with local roles only if necessary. We
#         # want to avoid as much overhead as possible.
#         user_roles = self.getRoles()
#         for role in object_roles:
#             if role in user_roles:
#                 if self._check_context(object):
#                     return 1
#                 return None

#         # check for local roles
#         lrmanagers = self._getLocalRolesPlugins()

#         for lrid, lrm in lrmanagers:
#             allowed = lrm.checkLocalRolesAllowed(self, object, object_roles)
#             # return values
#             # 0, 1, None
#             # - 1 success
#             # - 0 object context violation
#             # - None - failure
#             if allowed is None:
#                 continue
#             return allowed
#         return None

#     def setProperties(self, properties=None, **kw):
#         """ Set properties on a given user.

#         Accepts either keyword arguments or a mapping for the ``properties``
#         argument. The ``properties`` argument will take precedence over
#         keyword arguments if both are provided; no merging will occur.
#         """
#         if properties is None:
#             properties = kw

#         for sheet in self.getOrderedPropertySheets():
#             if not IMutablePropertySheet.providedBy(sheet):
#                 continue

#             update = {}
#             for (key, value) in properties.items():
#                 if sheet.hasProperty(key):
#                     update[key] = value
#                     del properties[key]

#             if update:
#                 sheet.setProperties(self, update)

#     def getProperty(self, id, default=_marker):
#         for sheet in self.getOrderedPropertySheets():
#             if sheet.hasProperty(id):
#                 value = sheet.getProperty(id)
#                 if isinstance(value, unicode):
#                     # XXX Temporarily work around the fact that
#                     # property sheets blindly store and return
#                     # unicode. This is sub-optimal and should be
#                     # dealed with at the property sheets level by
#                     # using Zope's converters.
#                     return value.encode('utf-8')
#                 return value

#         return default


class AnonymousUser(PloneUser):
    pass


@adapter(IRequest)
@implementer(IParticipation)
class PloneParticipation(object):
    """ User extraction.    """

    def __init__(self, request):
        self.request = request
        # Extract request user
        self.principal = self.extractUser()
        self.interaction = None

    def extractUser(self):
        pass
        # header_auth = self.request.headers.get('AUTHORIZATION')
        # if header_auth is None:
        #     return AnonymousUser(self.request)
        # else:
        #     schema, _, encoded_token = header_auth.partition(' ')
        #     if schema.lower() != 'bearer':
        #         raise ValueError('Authorization scheme is not Bearer')
        #     else:
        #         token = encoded_token.encode('ascii')
        #         PloneUser(self.request)

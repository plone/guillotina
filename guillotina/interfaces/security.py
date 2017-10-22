##############################################################################
#
# Copyright (c) 2001, 2002 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Security map to hold matrix-like relationships.

In all cases, 'setting' values are one of the defined constants
`Allow`, `Deny`, or `Unset`.
"""
from guillotina.i18n import MessageFactory
from guillotina.schema import Text
from guillotina.schema import TextLine
from zope.interface import Attribute
from zope.interface import Interface

import copyreg


_ = MessageFactory('guillotina')


Public = 'guillotina.Public'  # constant to check for always allowed permission

# These are the "setting" values returned by several methods defined
# in these interfaces.  The implementation may move to another
# location in the future, so this should be the preferred module to
# import these from.


class PermissionSetting(object):
    """PermissionSettings should be considered as immutable.
    They can be compared by identity. They are identified by
    their name.
    """

    def __new__(cls, name, description=None):
        """Keep a dict of PermissionSetting instances, indexed by
        name. If the name already exists in the dict, return that
        instance rather than creating a new one.
        """
        instances = cls.__dict__.get('_z_instances')
        if instances is None:
            cls._z_instances = instances = {}
        it = instances.get(name)
        if it is None:
            instances[name] = it = object.__new__(cls)
            it._init(name, description)
        return it

    def _init(self, name, description):
        self.__name = name
        self.__description = description

    def get_description(self):
        return self.__description

    def get_name(self):
        return self.__name

    def __str__(self):
        return 'PermissionSetting: %s' % self.__name

    __repr__ = __str__


# register PermissionSettings to be symbolic constants by identity,
# even when pickled and unpickled.
copyreg.constructor(PermissionSetting)
copyreg.pickle(PermissionSetting,
               PermissionSetting.get_name,
               PermissionSetting)


Allow = PermissionSetting(
    'Allow', 'Explicit allow setting for permissions')

Deny = PermissionSetting(
    'Deny', 'Explicit deny setting for permissions')

AllowSingle = PermissionSetting(
    'AllowSingle', 'Explicit allow and not inherit permission')

Unset = PermissionSetting(
    'Unset', 'Unset constant that denotes no setting for permission')


class IGroups(Interface):
    """A group Utility search."""


class IRole(Interface):
    """A role object."""

    id = TextLine(
        title='Id',
        description='Id as which this role will be known and used.',
        readonly=True,
        required=True)

    title = TextLine(
        title='Title',
        description='Provides a title for the role.',
        required=True)

    description = Text(
        title='Description',
        description='Provides a description for the role.',
        required=False)


class IPrincipalRoleMap(Interface):
    """Mappings between principals and roles."""

    def get_principals_for_role(role_id):  # noqa: N805
        """Get the principals that have been granted a role.

        Return the list of (principal id, setting) who have been assigned or
        removed from a role.

        If no principals have been assigned this role,
        then the empty list is returned.
        """

    def get_roles_for_principal(principal_id):  # noqa: N805
        """Get the roles granted to a principal.

        Return the list of (role id, setting) assigned or removed from
        this principal.

        If no roles have been assigned to
        this principal, then the empty list is returned.
        """

    def get_setting(role_id, principal_id, default=Unset):  # noqa: N805
        """Return the setting for this principal, role combination
        """

    def get_principals_and_roles():
        """Get all settings.

        Return all the principal/role combinations along with the
        setting for each combination as a sequence of tuples with the
        role id, principal id, and setting, in that order.
        """


class IPrincipalRoleManager(IPrincipalRoleMap):
    """Management interface for mappings between principals and roles."""

    def assign_role_to_principal(role_id, principal_id):  # noqa: N805
        """Assign the role to the principal."""

    def assign_role_to_principal_no_inherit(role_id, principal_id):  # noqa: N805
        """Assign the role to the principal."""

    def remove_role_from_principal(role_id, principal_id):  # noqa: N805
        """Remove a role from the principal."""

    def unset_role_for_principal(role_id, principal_id):  # noqa: N805
        """Unset the role for the principal."""


class IRolePermissionMap(Interface):
    """Mappings between roles and permissions."""

    def get_permissions_for_role(role_id):  # noqa: N805
        """Get the premissions granted to a role.

        Return a sequence of (permission id, setting) tuples for the given
        role.

        If no permissions have been granted to this
        role, then the empty list is returned.
        """

    def get_roles_for_permission(permission_id):  # noqa: N805
        """Get the roles that have a permission.

        Return a sequence of (role id, setting) tuples for the given
        permission.

        If no roles have been granted this permission, then the empty list is
        returned.
        """

    def get_setting(permission_id, role_id, default=Unset):  # noqa: N805
        """Return the setting for the given permission id and role id

        If there is no setting, Unset is returned
        """

    def get_roles_and_permissions():
        """Return a sequence of (permission_id, role_id, setting) here.

        The settings are returned as a sequence of permission, role,
        setting tuples.

        If no principal/role assertions have been made here, then the empty
        list is returned.
        """


class IRolePermissionManager(IRolePermissionMap):
    """Management interface for mappings between roles and permissions."""

    def grant_permission_to_role(permission_id, role_id):  # noqa: N805
        """Bind the permission to the role.
        """

    def grant_permission_to_role_no_inherit(role_id, principal_id):  # noqa: N805
        """Assign the role to the principal without local inherit."""

    def deny_permission_to_role(permission_id, role_id):  # noqa: N805
        """Deny the permission to the role
        """

    def unset_permission_from_role(permission_id, role_id):  # noqa: N805
        """Clear the setting of the permission to the role.
        """


class IPrincipalPermissionMap(Interface):
    """Mappings between principals and permissions."""

    def get_principals_for_permission(permission_id):  # noqa: N805
        """Get the principas that have a permission.

        Return the list of (principal_id, setting) tuples that describe
        security assertions for this permission.

        If no principals have been set for this permission, then the empty
        list is returned.
        """

    def get_permissions_for_principal(principal_id):  # noqa: N805
        """Get the permissions granted to a principal.

        Return the list of (permission, setting) tuples that describe
        security assertions for this principal.

        If no permissions have been set for this principal, then the empty
        list is returned.
        """

    def get_setting(permission_id, principal_id, default=Unset):  # noqa: N805
        """Get the setting for a permission and principal.

        Get the setting (Allow/Deny/Unset) for a given permission and
        principal.
        """

    def get_principals_and_permissions():
        """Get all principal permission settings.

        Get the principal security assertions here in the form
        of a list of three tuple containing
        (permission id, principal id, setting)
        """


class IPrincipalPermissionManager(IPrincipalPermissionMap):
    """Management interface for mappings between principals and permissions."""

    def grant_permission_to_principal(permission_id, principal_id):  # noqa: N805
        """Assert that the permission is allowed for the principal.
        """

    def grant_permission_to_principal_no_inherit(role_id, principal_id):  # noqa: N805
        """Assign the role to the principal without local inherit."""

    def deny_permission_to_principal(permission_id, principal_id):  # noqa: N805
        """Assert that the permission is denied to the principal.
        """

    def unset_permission_for_principal(permission_id, principal_id):  # noqa: N805
        """Remove the permission (either denied or allowed) from the
        principal.
        """


class IGrantInfo(Interface):
    """Get grant info needed for checking access
    """

    def principal_permission_grant(principal, permission):  # noqa: N805
        """Return the principal-permission grant if any

        The return value is one of Allow, Deny, or Unset
        """

    def get_roles_for_permission(permission):  # noqa: N805
        """Return the role grants for the permission

        The role grants are an iterable of role, setting tuples, where
        setting is either Allow or Deny.
        """

    def get_roles_for_principal(principal):  # noqa: N805
        """Return the role grants for the principal

        The role grants are an iterable of role, setting tuples, where
        setting is either Allow or Deny.
        """


class IInteraction(Interface):
    """A representation of an interaction between some actors and the system.
    """

    participations = Attribute("""An iterable of participations.""")

    def add(participation):  # noqa: N805
        """Add a participation."""

    def remove(participation):  # noqa: N805
        """Remove a participation."""

    def check_permission(permission, object):  # noqa: N805
        """Return whether security context allows permission on object.

        Arguments:
        permission -- A permission name
        object -- The object being accessed according to the permission
        """


class IPermission(Interface):
    """A permission object."""

    id = TextLine(
        title=_('Id'),
        description=_('Id as which this permission will be known and used.'),
        readonly=True,
        required=True)

    title = TextLine(
        title=_('Title'),
        description=_('Provides a title for the permission.'),
        required=True)

    description = Text(
        title=_('Description'),
        description=_('Provides a description for the permission.'),
        required=False)


class IPrincipal(Interface):
    """Principals are security artifacts that execute actions in a security
    environment.

    The most common examples of principals include user and group objects.

    It is likely that IPrincipal objects will have associated views
    used to list principals in management interfaces. For example, a
    system in which other meta-data are provided for principals might
    extend IPrincipal and register a view for the extended interface
    that displays the extended information. We'll probably want to
    define a standard view name (e.g.  'inline_summary') for this
    purpose.
    """

    id = TextLine(
        title=_('Id'),
        description=_('The unique identification of the principal.'),
        required=True,
        readonly=True)


class IParticipation(Interface):

    interaction = Attribute('The interaction')
    principal = Attribute('The authenticated principal')


class ISecurityPolicy(Interface):

    def __call__(participation=None):  # noqa: N805
        """Creates a new interaction for a given request.

        If participation is not None, it is added to the new interaction.
        """

# -*- coding: utf-8 -*-
from plone.server.catalog.interfaces import ICatalogDataAdapter
from plone.server.catalog.interfaces import ICatalogUtility
from plone.server.content import iterSchemataForType
from plone.server.directives import mergedTaggedValueDict
from plone.server.interfaces import CATALOG_KEY
from plone.server.interfaces import IUUID
from plone.server.security import getPrincipalsWithAccessContent
from plone.server.security import getRolesWithAccessContent
from plone.server.utils import get_content_path
from zope.component import queryAdapter
from zope.interface import implementer
from zope.schema import getFields
from zope.securitypolicy.principalpermission import principalPermissionManager
from zope.securitypolicy.rolepermission import rolePermissionManager
from zope.securitypolicy.settings import Allow


globalPrincipalPermissionSetting = principalPermissionManager.getSetting
globalRolesForPermission = rolePermissionManager.getRolesForPermission


@implementer(ICatalogUtility)
class DefaultSearchUtility(object):

    def __init__(self, settings):
        self.settings = settings

    async def search(self, query, site_id):
        pass

    async def getByUUID(self, uuid, site_id):
        pass

    async def getObjectByUUID(self, uuid, site_id):
        pass

    async def getByType(self, doc_type, site_id, query={}):
        pass

    async def getByPath(self, path, depth, site_id, doc_type=None):
        pass

    async def getFolderContents(self, parent_uuid, site_id, doc_type=None):
        pass

    async def index(self, datas, site_id):
        """
        {uid: <dict>}
        """
        pass

    async def remove(self, uids, site_id):
        """
        list of UIDs to remove from index
        """
        pass

    async def reindexAllContent(self, obj):
        """ For all Dexterity Content add a queue task that reindex the object
        """
        pass

    async def create_index(self, site_id):
        """ Creates an index
        """
        pass

    async def remove_index(self, site_id):
        """ Deletes an index
        """
        pass

    def get_data(self, content):
        data = {}
        adapter = queryAdapter(content, ICatalogDataAdapter)
        if adapter:
            data.update(adapter())
        return data


@implementer(ICatalogDataAdapter)
class DefaultCatalogDataAdapter(object):

    def __init__(self, content):
        self.content = content

    def __call__(self):

        # For each type
        values = {}
        for schema in iterSchemataForType(self.content.portal_type):
            # create export of the cataloged fields
            catalog = mergedTaggedValueDict(schema, CATALOG_KEY)
            for field_name, field in getFields(schema).items():
                kind_catalog = catalog.get(field_name, False)
                if kind_catalog:
                    real_field = field.bind(self.content)
                    value = real_field.get(self.content)
                    ident = schema.getName() + '-' + real_field.getName()
                    values[ident] = value

        # Look for plone.indexer
        # TODO

        # Global Roles

        roles = {}
        users = {}

        groles = globalRolesForPermission('plone.AccessContent')

        for r in groles:
            roles[r[0]] = r[1]

        # Local Roles

        lroles = getRolesWithAccessContent(self.content)
        lusers = getPrincipalsWithAccessContent(self.content)

        roles.update(lroles)
        users.update(lusers)

        path = get_content_path(self.content)

        values.update({
            'uuid': IUUID(self.content),
            'accessRoles': [x for x in roles if roles[x] == Allow],
            'accessUsers': [x for x in users if users[x] == Allow],
            'path': path,
            'portal_type': self.content.portal_type
        })

        if hasattr(self.content, '__parent__')\
                and self.content.__parent__ is not None:
            values['parent'] = IUUID(self.content.__parent__)
        return values

# -*- coding: utf-8 -*-
from plone.server.api.service import Service
from plone.server.catalog.interfaces import ICatalogUtility
from plone.server.catalog.interfaces import ICatalogDataAdapter
from plone.server.utils import get_content_path
from zope.component import queryUtility
from zope.interface import implementer
from zope.component import queryAdapter
from plone.dexterity.utils import iterSchemata
from plone.supermodel.interfaces import FIELDSETS_KEY
from plone.supermodel.interfaces import CATALOG_KEY
from plone.supermodel.interfaces import INDEX_KEY
from plone.supermodel.utils import mergedTaggedValueDict
from plone.dexterity.utils import iterSchemataForType
from zope.schema import getFields
from plone.server.utils import get_content_path
from zope.securitypolicy.settings import Allow
from plone.server.security import getRolesWithAccessContent
from plone.server.security import getPrincipalsWithAccessContent
import json
from plone.uuid.interfaces import IUUID

from zope.securitypolicy.principalpermission import principalPermissionManager
globalPrincipalPermissionSetting = principalPermissionManager.getSetting

from zope.securitypolicy.rolepermission import rolePermissionManager
globalRolesForPermission = rolePermissionManager.getRolesForPermission


class SearchGET(Service):
    async def __call__(self):
        q = self.request.GET.get('q')
        utility = queryUtility(ICatalogUtility)
        if not q or utility is None:
            return {
                'items_count': 0,
                'member': []
            }

        return await utility.search(q)


class ReindexPOST(Service):
    """ Creates index / catalog and reindex all content
    """
    async def __call__(self):
        utility = queryUtility(ICatalogUtility)
        await utility.reindexAllContent(self.request.site)
        return {}


@implementer(ICatalogUtility)
class DefaultSearchUtility(object):

    def __init__(self, settings):
        self.settings = settings

    async def search(self, query):
        pass

    async def index(self, datas, site_id):
        """
        {uid: <dict>}
        """
        pass

    async def remove(self, uids):
        """
        list of UIDs to remove from index
        """
        pass

    async def reindexAllContent(self, obj):
        """ For all Dexterity Content add a queue task that reindex the object
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
            index = mergedTaggedValueDict(schema, INDEX_KEY)
            for field_name, field in getFields(schema).items():
                kind_index = index.get(field_name, False)
                kind_catalog = catalog.get(field_name, False)
                if kind_catalog:
                    real_field = field.bind(self.content)
                    value = real_field.get(self.content)
                    ident = schema.getName() + '-' + real_field.getName()
                    values[ident] = value

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
            'path': path
        })

        if hasattr(self.content, '__parent__')\
                and self.content.__parent__ is not None:
            values['parent'] = IUUID(self.content.__parent__)
        return values

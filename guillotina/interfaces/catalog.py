from .content import IContainer
from guillotina.db.orm.interfaces import IBaseObject
from zope.interface import Interface

import typing


class ICatalogUtility(Interface):
    async def initialize(app):
        """
        initialization
        """

    async def search(container: IContainer, query: typing.Any):
        """
        Search parsed query
        """

    async def query(context: IBaseObject, query: typing.Any):
        """
        Raw search query, uses parser to transform query
        """

    async def index(container: IContainer, datas):
        """
        {uid: <dict>}
        """

    async def update(container: IContainer, datas):
        """
        {uid: <dict>}
        """

    async def remove(container: IContainer, uids):
        """
        list of UIDs to remove from index
        """

    async def reindex_all_content(context: IBaseObject, security=False):
        """ For all content add a queue task that reindex the object
        """

    async def initialize_catalog(container: IContainer):
        """ Creates an index
        """

    async def remove_catalog(container: IContainer):
        """ Deletes an index
        """

    async def get_data(content, indexes=None, schemas=None):
        """
        get data to index
        """


class IPGCatalogUtility(ICatalogUtility):
    """
    PG catalog utility
    """


class ISearchParser(Interface):
    def __init__(utility: ICatalogUtility, context: Interface):
        """
        """

    def __call__() -> typing.Any:
        """
        Translate the query
        """


class ICatalogDataAdapter(Interface):
    """
    """

    async def __call__(indexes=None, schemas=None):
        """
        Return a dictionary of [index name, value]
        """


class ISecurityInfo(Interface):
    """
    """

    async def __call__(indexes=None, schemas=None):
        """
        Return a dictionary of [index name, value]
        """

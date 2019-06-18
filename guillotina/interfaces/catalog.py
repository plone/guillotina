import typing

from zope.interface import Interface


class ICatalogUtility(Interface):
    def reindex_all_content(container):  # noqa: N805
        '''
        '''

    def initialize_catalog(container):  # noqa: N805
        '''
        '''

    def remove_catalog(container):  # noqa: N805
        '''
        '''

    def search(container, q: str):  # noqa: N805
        """
        String search query
        """

    def query(container, q: dict):  # noqa: N805
        """
        Raw query
        """


class IPGCatalogUtility(ICatalogUtility):
    '''
    PG catalog utility
    '''


class ISearchParser(Interface):
    def __init__(utility: ICatalogUtility, context: Interface):
        '''
        '''

    def __call__() -> typing.Any:
        '''
        Translate the query
        '''


class ICatalogDataAdapter(Interface):
    '''
    '''

    async def __call__(indexes=None, schemas=None):
        '''
        Return a dictionary of [index name, value]
        '''


class ISecurityInfo(Interface):
    '''
    '''

    async def __call__(indexes=None, schemas=None):
        '''
        Return a dictionary of [index name, value]
        '''

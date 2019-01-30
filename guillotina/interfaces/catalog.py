from zope.interface import Interface


class ICatalogUtility(Interface):
    def get_by_uuid(container, uid):  # noqa: N805
        '''
        '''

    def get_object_by_uuid(container, uid):  # noqa: N805
        '''
        '''

    def get_by_type(container, type_id):  # noqa: N805
        '''
        '''

    def get_by_path(container, path):  # noqa: N805
        '''
        '''

    def get_folder_contents(container, obj):  # noqa: N805
        '''
        '''

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

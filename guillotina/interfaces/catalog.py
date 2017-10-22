from zope.interface import Interface


class ICatalogUtility(Interface):
    def get_by_uuid(container, uid):  # noqa: N805
        pass

    def get_object_by_uuid(container, uid):  # noqa: N805
        pass

    def get_by_type(container, type_id):  # noqa: N805
        pass

    def get_by_path(container, path):  # noqa: N805
        pass

    def get_folder_contents(container, obj):  # noqa: N805
        pass

    def reindex_all_content(container):  # noqa: N805
        pass

    def initialize_catalog(container):  # noqa: N805
        pass

    def remove_catalog(container):  # noqa: N805
        pass

    def search(container, q: str):  # noqa: N805
        """
        String search query
        """

    def query(container, q: dict):  # noqa: N805
        """
        Raw query
        """


class ICatalogDataAdapter(Interface):
    pass


class ISecurityInfo(Interface):
    pass

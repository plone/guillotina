# -*- coding: utf-8 -*-
from zope.interface import Interface


class ICatalogUtility(Interface):
    def get_by_uuid(container, uid):
        pass

    def get_object_by_uuid(container, uid):
        pass

    def get_by_type(container, type_id):
        pass

    def get_by_path(container, path):
        pass

    def get_folder_contents(container, obj):
        pass

    def reindex_all_content(container):
        pass

    def initialize_catalog(container):
        pass

    def remove_catalog(container):
        pass

    def search(container, q: str):
        """
        String search query
        """

    def query(container, q: dict):
        """
        Raw query
        """


class ICatalogDataAdapter(Interface):
    pass


class ISecurityInfo(Interface):
    pass

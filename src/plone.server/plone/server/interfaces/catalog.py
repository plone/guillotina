# -*- coding: utf-8 -*-
from zope.interface import Interface


class ICatalogUtility(Interface):
    def get_by_uuid(site, uid):
        pass

    def get_object_by_uuid(site, uid):
        pass

    def get_by_type(site, type_id):
        pass

    def get_by_path(site, path):
        pass

    def get_folder_contents(site, obj):
        pass

    def reindex_all_content(site):
        pass

    def initialize_catalog(site):
        pass

    def remove_catalog(site):
        pass

    def search(site, q: str):
        """
        String search query
        """

    def query(site, q: dict):
        """
        Raw query
        """


class ICatalogDataAdapter(Interface):
    pass

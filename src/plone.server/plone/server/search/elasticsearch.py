# -*- coding: utf-8 -*-
from aioes import Elasticsearch
from aioes.exception import ConnectionError
from aioes.exception import RequestError
from aioes.exception import TransportError
from plone.server.search.search import DefaultSearchUtility

import logging


logger = logging.getLogger('plone.server')


class ElasticSearchUtility(DefaultSearchUtility):

    bulk_size = 50
    index_name = 'plone'
    doc_type = 'plone'
    initialized = False

    def __init__(self, settings):
        self.settings = settings
        self.index_index = settings['index_name']
        self.doc_type = settings['doc_type']
        self.bulk_size = settings.get('bulk_size', 50)

    async def _init_el(self):
        # need delayed setup here since __init__ can not return a future
        conn = self.get_connection()
        try:
            await conn.indices.create(self.index_name)
        except TransportError:
            pass
        except ConnectionError:
            logger.warn('elasticsearch not installed', exc_info=True)
            return
        except RequestError:
            pass

        mapping = {'properties': self.settings['mapping']}
        try:
            await conn.indices.put_mapping(
                self.index_name, self.doc_type, body=mapping)
        except:
            logger.warn('elasticsearch not installed', exc_info=True)
        self.initialized = True

    def get_connection(self):
        return Elasticsearch(**self.settings['connection_settings'])

    async def search(self, q):
        query = {
            'match': {
                'title': q
            }
        }
        result = await self.get_connection().search(
            index=self.index_name,
            doc_type=self.doc_type,
            body={'query': query})
        items = []
        for item in result['hits']['hits']:
            data = item['_source']
            data.update({
                '@id': 'http://<get-url>:55001' + data.get('path', ''),
                '@type': data.get('portal_type'),
            })
            items.append(data)
        return {
            'items_count': result['hits']['total'],
            'member': items
        }

    async def index(self, datas):
        """
        {uid: <dict>}
        """
        if not self.initialized:
            await self._init_el()

        if len(datas) > 0:
            bulk_data = []

            connection = self.get_connection()

            for uid, data in datas.items():
                bulk_data.extend([{
                    'index': {
                        '_index': self.index_name,
                        '_type': self.doc_type,
                        '_id': uid
                    }
                }, data])
                if len(bulk_data) % self.bulk_size == 0:
                    await connection.bulk(
                        index=self.index_name, doc_type=self.doc_type,
                        body=bulk_data)
                    bulk_data = []

            if len(bulk_data) > 0:
                await connection.bulk(
                    index=self.index_name, doc_type=self.doc_type,
                    body=bulk_data)

    async def remove(self, uids):
        """
        list of UIDs to remove from index
        """
        if len(uids) > 0:
            bulk_data = []
            for uid in uids:
                bulk_data.append({
                    'delete': {
                        '_index': self.index_name,
                        '_type': self.doc_type,
                        '_id': uid
                    }
                })
            await self.get_connection().bulk(
                index=self.index_name, doc_type=self.doc_type, body=bulk_data)

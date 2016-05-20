import logging

from aioes import Elasticsearch
from aioes.exception import ConnectionError
from aioes.exception import RequestError
from aioes.exception import TransportError
from plone.server.search.search import DefaultSearchUtility


logger = logging.getLogger('plone.server')


class ElasticSearchUtility(DefaultSearchUtility):

    bulk_size = 50
    index_name = 'plone'
    doc_type = 'plone'

    def __init__(self, settings):
        self.settings = settings
        self.index_index = settings['index_name']
        self.doc_type = settings['doc_type']
        self.bulk_size = settings.get('bulk_size', 50)
        self._init_el()

    def _init_el(self):
        conn = self.get_connection()
        try:
            conn.indices.create(self.index_name)
        except TransportError:
            pass
        except ConnectionError:
            logger.warn('elasticsearch not installed', exc_info=True)
            return
        except RequestError:
            pass

        mapping = {'properties': self.settings['mapping']}
        try:
            conn.indices.put_mapping(self.index_name, self.doc_type, body=mapping)
        except:
            logger.warn('elasticsearch not installed', exc_info=True)

    def get_connection(self):
        return Elasticsearch(**self.settings['connection_settings'])

    async def search(self, q):
        import pdb; pdb.set_trace()
        query = {
            'filtered': {
                'filter': {},
                "query": {
                    "dis_max": {
                        "queries": [{
                            "match_phrase": {
                                'text': {
                                    'query': q,
                                    'slop': 50
                                }
                            }
                        }]
                    }
                }
            }
        }
        result = await self.get_connection().search(
            index=self.index_name,
            doc_type=self.doc_type,
            body={'query': query})
        items = []
        for item in result['hits']['hits']:
            items.append({
                "@id": "http://localhost:55001/plone/robot-test-folder",
                "@type": "Folder",
                "description": item['description'],
                "title": item['title']
            })
        return {
            "items_count": result['hits']['total'],
            "member": items
        }

    def index(self, datas):
        """
        {uid: <dict>}
        """
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
                    connection.bulk(index=self.index_name, doc_type=self.doc_type, body=bulk_data)
                    bulk_data = []

            if len(bulk_data) > 0:
                connection.bulk(index=self.index_name, doc_type=self.doc_type, body=bulk_data)

    def remove(self, uids):
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
            self.get_connection().bulk(index=self.index_name, doc_type=self.doc_type,
                                       body=bulk_data)

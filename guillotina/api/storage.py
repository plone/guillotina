from guillotina import configure
from guillotina._settings import app_settings
from guillotina.component import get_adapter
from guillotina.db.interfaces import IDatabaseManager
from guillotina.interfaces import IApplication
from guillotina.response import HTTPNotFound
from guillotina.utils import list_or_dict_items

import re


@configure.service(
    context=IApplication, method='GET', permission='guillotina.GetDatabases',
    name='@storages')
async def storages_get(context, request):
    result = []
    for key, dbconfig in list_or_dict_items(app_settings['storages']):
        result.append({
            'id': key,
            'type': dbconfig['storage']
        })
    return result


def _get_storage_config(storage_id):
    for key, dbconfig in list_or_dict_items(app_settings['storages']):
        if key == storage_id:
            dbconfig['storage_id'] = storage_id
            return dbconfig


@configure.service(
    context=IApplication, method='GET', permission='guillotina.GetDatabases',
    name='@storages/{storage_id}')
async def storage_get(context, request):
    storage_id = request.matchdict['storage_id']
    config = _get_storage_config(storage_id)
    if config is None:
        raise HTTPNotFound(content={
            'reason': f'Storage {storage_id}'
        })
    manager = config.get('type', config['storage'])
    factory = get_adapter(context, IDatabaseManager,
                          name=manager, args=[config])
    return {
        'id': storage_id,
        'type': config['storage'],
        'databases': await factory.get_names()
    }


@configure.service(
    context=IApplication, method='POST', permission='guillotina.MountDatabase',
    name='@storages/{storage_id}')
async def storage_create_db(context, request):
    storage_id = request.matchdict['storage_id']
    config = _get_storage_config(storage_id)
    if config is None:
        raise HTTPNotFound(content={
            'reason': f'Storage {storage_id}'})
    manager = config.get('type', config['storage'])
    factory = get_adapter(context, IDatabaseManager,
                          name=manager, args=[config])
    data = await request.json()
    name = data['name']
    assert name == re.escape(name)
    await factory.create(data['name'])


@configure.service(
    context=IApplication, method='DELETE', permission='guillotina.UmountDatabase',
    name='@storages/{storage_id}/{db_id}')
async def delete_db(context, request):
    storage_id = request.matchdict['storage_id']
    config = _get_storage_config(storage_id)
    if config is None:
        raise HTTPNotFound(content={
            'reason': f'Storage {storage_id}'})
    manager = config.get('type', config['storage'])
    factory = get_adapter(context, IDatabaseManager,
                          name=manager, args=[config])
    assert request.matchdict['db_id'] in await factory.get_names()
    await factory.delete(request.matchdict['db_id'])


@configure.service(
    context=IApplication, method='GET', permission='guillotina.GetDatabases',
    name='@storages/{storage_id}/{db_id}')
async def get_db(context, request):
    storage_id = request.matchdict['storage_id']
    config = _get_storage_config(storage_id)
    if config is None:
        raise HTTPNotFound(content={
            'reason': f'Storage {storage_id}'})
    manager = config.get('type', config['storage'])
    factory = get_adapter(context, IDatabaseManager,
                          name=manager, args=[config])
    db_id = request.matchdict['db_id']
    db = await factory.get_database(db_id)
    return {
        'id': db.id,
        'storage_id': storage_id,
        'type': config['storage']
    }

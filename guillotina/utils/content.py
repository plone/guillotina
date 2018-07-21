from .misc import get_current_request
from guillotina import glogging
from guillotina.component import get_utility
from guillotina.component import query_multi_adapter
from guillotina.db.reader import reader
from guillotina.interfaces import IAbsoluteURL
from guillotina.interfaces import IApplication
from guillotina.interfaces import IContainer
from guillotina.interfaces import IDatabase
from guillotina.interfaces import IPrincipalRoleMap
from guillotina.interfaces import IRequest
from guillotina.interfaces import IResource

import string
import typing


logger = glogging.getLogger('guillotina')


def get_content_path(content: IResource) -> str:
    """
    Generate full path of resource object

    :param content: object to get path from
    """
    parts = []
    parent = getattr(content, '__parent__', None)
    while content is not None and content.__name__ is not None and\
            parent is not None and not IContainer.providedBy(content):
        parts.append(content.__name__)
        content = parent
        parent = getattr(content, '__parent__', None)
    return '/' + '/'.join(reversed(parts))


def get_content_depth(content: IResource) -> int:
    """
    Calculate the depth of a resource object
    """
    depth = 0
    for _ in iter_parents(content):
        depth += 1
    return depth


def iter_parents(content: IResource) -> typing.Iterator[IResource]:
    """
    Iterate through all the parents of a content object

    :param content: object to get path from
    """
    content = getattr(content, '__parent__', None)
    while content is not None:
        yield content
        content = getattr(content, '__parent__', None)


_valid_id_characters = string.digits + string.ascii_lowercase + '.-_@$^()+'


def valid_id(_id):
    _id = _id.lower()
    # can't start with _
    if not _id or _id[0] in ('_', '@'):
        return False
    return _id == ''.join([l for l in _id if l in _valid_id_characters])


async def get_containers(request):
    root = get_utility(IApplication, name='root')
    for _id, db in root:
        if IDatabase.providedBy(db):
            tm = request._tm = db.get_transaction_manager()
            request._db_id = _id
            async with tm.lock:
                # reset _txn to make sure to create a new ob
                request._txn = None
                txn = await tm.begin(request)
                items = {}
                async for c_id, container in db.async_items():
                    items[c_id] = container
                await tm.abort(txn=txn)

            for _, container in items.items():
                request._txn = txn = await tm.begin(request)
                container._p_jar = request._txn
                request.container = container
                request._container_id = container.id
                if hasattr(request, 'container_settings'):
                    del request.container_settings
                yield txn, tm, container
                try:
                    # do not rely on consumer of object to always close it.
                    # there is no harm in aborting twice
                    await tm.abort(txn=txn)
                except Exception:
                    logger.warn('Error aborting transaction', exc_info=True)


def get_owners(obj: IResource) -> list:
    '''
    Return owners of an object

    :param obj: object to get path from
    '''
    try:
        prinrole = IPrincipalRoleMap(obj)
    except TypeError:
        return []
    owners = []
    for user, roles in prinrole._bycol.items():
        for role in roles:
            if role == 'guillotina.Owner':
                owners.append(user)
    if len(owners) == 0 and getattr(obj, '__parent__', None) is not None:
        # owner can be parent if none found on current object
        return get_owners(obj.__parent__)
    return owners


async def navigate_to(obj: IResource, path: str):
    '''
    Get a sub-object.

    :param obj: object to get path from
    :param path: relative path to object you want to retrieve
    '''
    actual = obj
    path_components = path.strip('/').split('/')
    for p in path_components:
        if p != '':
            item = await actual.async_get(p)
            if item is None:
                raise KeyError('No %s in %s' % (p, actual))
            else:
                actual = item
    return actual


def get_object_url(ob: IResource,
                   request: IRequest=None,
                   **kwargs) -> typing.Optional[str]:
    '''
    Generate full url of object.

    :param ob: object to get url for
    :param request: relative path to object you want to retrieve
    '''
    if request is None:
        request = get_current_request()
    url_adapter = query_multi_adapter((ob, request), IAbsoluteURL)
    if url_adapter is not None:
        return url_adapter(**kwargs)
    return None


async def get_object_by_oid(oid: str, txn=None) -> IResource:
    '''
    Get an object from an oid
    '''
    if txn is None:
        from guillotina.transactions import get_transaction
        txn = get_transaction()
    result = txn._manager._hard_cache.get(oid, None)
    if result is None:
        result = await txn._get(oid)

    obj = reader(result)
    obj._p_jar = txn
    if result['parent_id']:
        obj.__parent__ = await get_object_by_oid(result['parent_id'], txn)
    return obj

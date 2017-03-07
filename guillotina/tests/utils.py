from aiohttp.test_utils import make_mocked_request
from zope.interface import alsoProvides
from guillotina.interfaces import IDefaultLayer
from guillotina.interfaces import IRequest


def get_mocked_request(db):
    request = make_mocked_request('POST', '/')
    request._db_id = db.id
    request._tm = db.new_transaction_manager()
    request._tm.request = request  # so get_current_request can find it...
    alsoProvides(request, IRequest)
    alsoProvides(request, IDefaultLayer)
    return request


async def get_root(request):
    await request._tm.begin(request=request)
    return await request._tm.root()

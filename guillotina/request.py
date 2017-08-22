from aiohttp import web_request
from guillotina.interfaces import IDefaultLayer
from guillotina.interfaces import IRequest
from zope.interface import implementer


@implementer(IRequest, IDefaultLayer)
class Request(web_request.Request):
    """
    Guillotina specific request type.
    We store potentially a lot of state onto the request
    object as it is essential our poor man's thread local model
    """

#    _db_id = None
#    _tm = None
#    _txn = None
#    _container_id = None
#    container = None
#    container_settings = None
#    tail = None
#    resource = None
#    security = None

    _db_write_enabled = True
    _futures = None

    application = None
    exc = None
    view_name = None
    found_view = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._futures = {}

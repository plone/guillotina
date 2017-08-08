from aiohttp import web_request


class Request(web_request.Request):
    """
    Guillotina specific request type.
    We store potentially a lot of state onto the request
    object as it is essential our poor man's thread local model
    """

    _db_write_enabled = True
    _db_id = None
    _tm = None
    _txn = None
    _container_id = None
    _futures = None

    application = None
    container = None
    container_settings = None
    tail = None
    resource = None
    exc = None
    matched_view = None
    security = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._futures = {}

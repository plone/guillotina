from guillotina import task_vars

import logging
import uuid


def _wrapped(name):
    def log(self, *args, **kwargs):
        from guillotina.utils import get_authenticated_user_id
        from guillotina.utils import get_current_request
        from guillotina.exceptions import RequestNotFound

        func = getattr(self._logger, name)
        request = kwargs.pop("request", None)
        eid = kwargs.pop("eid", None)
        if request is None:
            try:
                request = get_current_request()
            except RequestNotFound:
                pass
        if request is not None:
            if eid is None:
                eid = uuid.uuid4().hex
            extra = kwargs.get("extra", {})
            try:
                url = request.url.human_repr()
            except AttributeError:
                # older version of aiohttp
                url = request.path
            try:
                agent = request.headers["User-Agent"]
            except (AttributeError, KeyError):
                agent = "Unknown"
            container = task_vars.container.get()
            db = task_vars.db.get()
            extra.update(
                {
                    "method": request.method,
                    "url": url,
                    "container": getattr(container, "id", None),
                    "account": getattr(container, "id", None),
                    "db_id": getattr(db, "id", None),
                    "user": get_authenticated_user_id() or "Anonymous",
                    "eid": eid,
                    "agent": agent,
                    # in case a fake req object doesn't use the guillotina Request object
                    "request_uid": getattr(request, "uid", None),
                }
            )
            kwargs["extra"] = extra
        return func(*args, **kwargs)

    return log


class Logger:
    def __init__(self, logger_name):
        self._logger = logging.getLogger(logger_name)

    exception = _wrapped("exception")
    warning = _wrapped("warning")
    warn = _wrapped("warn")
    error = _wrapped("error")
    info = _wrapped("info")
    debug = _wrapped("debug")


def getLogger(name):  # noqa: N802
    return Logger(name)

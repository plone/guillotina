from guillotina.utils import get_content_path
from guillotina.interfaces import IApplication


def get_url(req, path=""):
    return "{}://{}/{}".format(get_scheme(req), req.host, path.lstrip("/"))


def get_ip(req):
    ip = req.headers.get("X-Forwarded-For", req.headers.get("X-Real-IP", None))
    if ip is not None:
        return ip
    peername = req.transport.get_extra_info("peername")
    if peername is not None:
        host, port = peername
        return host
    return "unknown"


def get_scheme(req):
    scheme = req.headers.get(
        "X-Forwarded-Protocol",
        req.headers.get(
            "X-Scheme", req.headers.get("X-Forwarded-Proto", None)
        ),
    )

    if scheme:
        return scheme

    return req.scheme


def get_full_content_path(request, ob):
    path = "/"
    if hasattr(request, "_db_id"):
        path += request._db_id + "/"
    if hasattr(request, "container"):
        path += request.container.__name__ + "/"
    if IApplication.providedBy(ob):
        return path
    return (
        "{}{}".format(path, get_content_path(ob))
        .replace("//", "/")
        .rstrip("/")
    )

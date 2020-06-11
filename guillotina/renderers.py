from guillotina import configure
from guillotina.interfaces import IResponse
from guillotina.interfaces.security import PermissionSetting
from guillotina.profile import profilable
from guillotina.response import Response
from typing import cast
from typing import Optional
from zope.interface.interface import InterfaceClass

import json
import orjson


def guillotina_json_default(obj):
    if isinstance(obj, str):
        if type(obj) != str:  # e.g, i18n.Message()
            return str(obj)
    elif isinstance(obj, complex):
        return [obj.real, obj.imag]
    elif isinstance(obj, type):
        return obj.__module__ + "." + obj.__name__
    elif isinstance(obj, InterfaceClass):
        return [x.__module__ + "." + x.__name__ for x in obj.__iro__]  # noqa
    elif isinstance(obj, dict):
        if type(obj) != dict:  # e.g. collections.OrderedDict
            return dict(obj)

    try:
        iterable = iter(obj)
    except TypeError:
        pass
    else:
        return list(iterable)

    if isinstance(obj, PermissionSetting):
        return obj.get_name()
    if callable(obj):
        return obj.__module__ + "." + obj.__name__

    raise TypeError("Unable to serialize %r (type: %s)" % (obj, type(obj)))


# b/w compat
class GuillotinaJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        return guillotina_json_default(obj)


class Renderer:
    content_type: str

    def __init__(self, view, request):
        self.view = view
        self.request = request

    def get_body(self, value) -> Optional[bytes]:
        return str(value).encode("utf-8")

    @profilable
    async def __call__(self, value) -> Response:
        """
        Value can be:
        - Guillotina response object
        - serializable value
        """
        if IResponse.providedBy(value):
            resp = cast(Response, value)
            if resp.content is not None:
                resp.set_body(self.get_body(resp.content), self.content_type)
            return resp

        return Response(body=self.get_body(value) or b"", status=200, content_type=self.content_type)


@configure.renderer(name="application/json")
@configure.renderer(name="*/*")
class RendererJson(Renderer):
    content_type = "application/json"

    def get_body(self, value) -> Optional[bytes]:
        if value is not None:
            return orjson.dumps(value, default=guillotina_json_default)
        return None


class StringRenderer(Renderer):
    content_type = "text/plain"

    def get_body(self, value) -> bytes:
        if not isinstance(value, bytes):
            if isinstance(value, str):
                value = value.encode("utf8")
            else:
                value = orjson.dumps(value)
        return value


@configure.renderer(name="text/html")
@configure.renderer(name="text/*")
class RendererHtml(Renderer):
    content_type = "text/html"

    def get_body(self, value: IResponse) -> Optional[bytes]:
        body = super().get_body(value)
        if body is not None:
            if b"<html" not in body:
                body = b"<html><body>" + body + b"</body></html>"
        return body


@configure.renderer(name="text/plain")
class RendererPlain(StringRenderer):
    content_type = "text/plain"

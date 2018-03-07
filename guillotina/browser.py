from aiohttp.web import Response as aioResponse
from guillotina import configure
from guillotina import error_reasons
from guillotina.component import adapter
from guillotina.exc_resp import render_error_response
from guillotina.interfaces import IAbsoluteURL
from guillotina.interfaces import ILocation
from guillotina.interfaces import IRequest
from guillotina.interfaces import IResource
from guillotina.interfaces import ISerializableException
from guillotina.interfaces import IView
from guillotina.utils import get_current_request
from zope.interface import implementer


def get_physical_path(context):
    parts = [context.__name__]
    parent = context.__parent__
    while parent is not None and parent.__name__ is not None:
        parts.append(parent.__name__)
        parent = parent.__parent__
    parts.append('')
    return [x for x in reversed(parts)]


@adapter(IResource, IRequest)
@implementer(IView, ILocation)
class View(object):

    __name__ = 'view'

    # An attribute that marks that a view should not
    # be unauthorized by AccessContent on the object
    # Should always be False unless you provide auth
    # by another mechanism on the view

    __allow_access__ = False
    __read_only__ = None

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @property
    def __parent__(self):
        return self.context

    async def __call__(self):
        return {
            'context': str(self.context),
            'path': '/'.join(get_physical_path(self.context))
        }


@configure.adapter(
    for_=(IResource, IRequest),  # noqa: N801
    provides=IAbsoluteURL)
class Absolute_URL(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, relative=False, container_url=False):
        if container_url:
            # we want the url relative to container so remove the container
            path = [x for x in get_physical_path(self.context)]
            path.pop(1)
            path = '/'.join(path)
        else:
            path = '/'.join(get_physical_path(self.context))

        if 'X-VirtualHost-Monster' in self.request.headers:
            virtualhost = self.request.headers['X-VirtualHost-Monster']
        else:
            virtualhost = None

        if container_url:
            return path
        elif relative:
            return '/' + self.request._db_id + path
        elif virtualhost:
            return virtualhost + self.request._db_id + path
        else:
            if 'X-Forwarded-Proto' in self.request.headers:
                scheme = self.request.headers['X-Forwarded-Proto']
            else:
                scheme = self.request.scheme
            return scheme + '://' + (self.request.host or 'localhost') + '/' +\
                self.request._db_id + path


@configure.adapter(
    for_=IResource,  # noqa: N801
    provides=IAbsoluteURL)
class Absolute_URL_ObtainRequest(Absolute_URL):

    def __init__(self, context):
        request = get_current_request()
        super(Absolute_URL_ObtainRequest, self).__init__(context, request)


class Response(object):
    """Middle response to be rendered."""

    _missing_status_code = 200

    def __init__(self, response={}, headers={}, status=None):
        self.response = response
        self.headers = headers
        if status is None:
            if isinstance(response, aioResponse):
                self.status = response.status
            else:
                self.status = self._missing_status_code
        else:
            self.status = status
            if status == 204:
                # 204 is not allowed to have content
                self.response = ''


class UnauthorizedResponse(Response):
    _missing_status_code = 401

    def __init__(self, message, headers={}, status=None, eid=None):
        response = {
            'error': {
                'type': 'Unauthorized',
                'message': message
            }
        }
        response.update(
            render_error_response('Unauthorized', error_reasons.UNAUTHORIZED, eid))
        super(UnauthorizedResponse, self).__init__(response, headers, status)


class ErrorResponse(Response):
    _missing_status_code = 500

    def __init__(self, type, message, exc=None, headers={}, status=None,
                 reason=error_reasons.UNKNOWN, eid=None):
        data = {
            'type': type,
            'message': message
        }
        if ISerializableException.providedBy(exc):
            data.update(exc.json_data())
        response = {
            'error': data
        }
        if reason is not None:
            response.update(render_error_response(type, reason, eid))
        super(ErrorResponse, self).__init__(response, headers, status)

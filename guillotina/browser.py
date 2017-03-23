# -*- coding: utf-8 -*-
from guillotina import configure
from guillotina.component import adapter
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
    for_=(IResource, IRequest),
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
            return self.request.scheme + '://' + (self.request.host or 'localhost') + '/' +\
                self.request._db_id + path


@configure.adapter(
    for_=IResource,
    provides=IAbsoluteURL)
class Absolute_URL_ObtainRequest(Absolute_URL):

    def __init__(self, context):
        request = get_current_request()
        super(Absolute_URL_ObtainRequest, self).__init__(context, request)


class Response(object):
    """Middle response to be rendered."""

    def __init__(self, response={}, headers={}, status=200):
        self.response = response
        self.headers = headers
        self.status = status


class UnauthorizedResponse(Response):

    def __init__(self, message, headers={}, status=401):
        response = {
            'error': {
                'type': 'Unauthorized',
                'message': message
            }
        }
        super(UnauthorizedResponse, self).__init__(response, headers, status)


class ErrorResponse(Response):

    def __init__(self, type, message, exc=None, headers={}, status=400):
        data = {
            'type': type,
            'message': message
        }
        if ISerializableException.providedBy(exc):
            data.update(exc.json_data())
        response = {
            'error': data
        }
        super(ErrorResponse, self).__init__(response, headers, status)

# -*- coding: utf-8 -*-
from plone.dexterity.interfaces import IDexterityContent
from plone.server.interfaces import IRequest
from plone.server.interfaces import IView
from plone.server.interfaces import IAbsoluteURL
from plone.server.transactions import get_current_request
from zope.component import adapter
from zope.interface import implementer
from zope.location import ILocation


def get_physical_path(context):
    parts = [context.__name__]
    parent = context.__parent__
    while parent is not None and parent.__name__ is not None:
        parts.append(parent.__name__)
        parent = parent.__parent__
    parts.append('')
    return reversed(parts)


@adapter(IDexterityContent, IRequest)
@implementer(IView, ILocation)
class View(object):

    __name__ = 'view'

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


@adapter(IDexterityContent, IRequest)
@implementer(IAbsoluteURL)
class Absolute_URL(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, relative=False, site_url=False):
        if site_url:
            # we want the url relative to site so remove the site
            path = [x for x in get_physical_path(self.context)]
            path.pop(1)
            path = '/'.join(path)
        else:
            path = '/'.join(get_physical_path(self.context))

        if site_url:
            return path
        elif relative:
            return '/' + self.request._db_id + path
        else:
            return self.request.scheme + '://' + self.request.host + '/' +\
                self.request._db_id + path


@adapter(IDexterityContent)
@implementer(IAbsoluteURL)
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

    def __init__(self, type, message, headers={}, status=400):
        response = {
            'error': {
                'type': type,
                'message': message
            }
        }
        super(ErrorResponse, self).__init__(response, headers, status)



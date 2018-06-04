from guillotina import configure
from guillotina.component import adapter
from guillotina.interfaces import IAbsoluteURL
from guillotina.interfaces import ILocation
from guillotina.interfaces import IRequest
from guillotina.interfaces import IResource
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
        super().__init__(context, request)

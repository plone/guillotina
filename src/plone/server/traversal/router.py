import asyncio
import logging
import sys
import types

from aiohttp.abc import AbstractRouter, AbstractMatchInfo
from aiohttp.web_exceptions import HTTPNotFound

from resolver_deco import resolver
from .traversal import traverse

log = logging.getLogger(__name__)

if sys.version_info >= (3, 5, 0):  # b/c for 3.4
    SIMPLE_VIEWS_TYPES = (types.FunctionType, types.CoroutineType)
else:
    SIMPLE_VIEWS_TYPES = (types.FunctionType,)


class ViewNotResolved(Exception):
    """ Raised from Application.resolve_view.
    """
    def __init__(self, request, resource, tail):
        super().__init__(request, resource, tail)
        self.request = request
        self.resource = resource
        self.tail = tail


class BaseMatchInfo(AbstractMatchInfo):
    route = None

    @asyncio.coroutine
    def expect_handler(self, request):
        return None

    @property
    def http_exception(self):
        return None


class MatchInfo(BaseMatchInfo):
    def __init__(self, request, resource, tail, view):
        self.request = request
        self.resource = resource
        self.tail = tail
        self.view = view

    def handler(self, request):
        if isinstance(self.view, SIMPLE_VIEWS_TYPES):
            return self.view(self.request, self.resource, self.tail)
        else:
            return self.view()

    def get_info(self):
        return {
            'request': self.request,
            'resource': self.resource,
            'tail': self.tail,
            'view': self.view,
        }


class TraversalExceptionMatchInfo(BaseMatchInfo):
    def __init__(self, request, exc):
        self.request = request
        self.exc = exc

    def handler(self, request):
        raise self.exc

    def get_info(self):
        return {
            'request': self.request,
            'exc': self.exc,
        }


class TraversalRouter(AbstractRouter):
    _root_factory = None

    @resolver('root_factory')
    def __init__(self, root_factory=None):
        self.set_root_factory(root_factory)
        self.resources = {}
        self.exceptions = {}

    @asyncio.coroutine
    def resolve(self, request):
        import pdb; pdb.set_trace()
        try:
            resource, tail = yield from self.traverse(request)
            exc = None
        except Exception as _exc:
            resource = None
            tail = None
            exc = _exc

        request.resource = resource
        request.tail = tail
        request.exc = exc

        if resource is not None:
            try:
                # Adapter!!!
                view = self.resolve_view(request, resource, tail)
            except ViewNotResolved:
                return TraversalExceptionMatchInfo(request, HTTPNotFound())

            return MatchInfo(request, resource, tail, view)
        else:
            return TraversalExceptionMatchInfo(request, exc)

    @asyncio.coroutine
    def traverse(self, request, *args, **kwargs):
        path = tuple(p for p in request.path.split('/') if p)
        root = self.get_root(request.app, *args, **kwargs)
        if path:
            return (yield from traverse(root, path, request))
        else:
            return root, path

    @resolver('root_factory')
    def set_root_factory(self, root_factory):
        """ Set root resource class.
        Analogue of the "set_root_factory" method from pyramid framework.
        """
        self._root_factory = root_factory

    def get_root(self, app, *args, **kwargs):
        """ Create new root resource instance.
        """
        return self._root_factory(app, *args, **kwargs)

    @resolver('resource')
    def resolve_view(self, request, resource, tail=()):
        """ Resolve view for resource and tail.
        """
        if isinstance(resource, type):
            resource_class = resource
        else:
            resource_class = resource.__class__

        for rc in resource_class.__mro__[:-1]:
            if rc in self.resources:
                if 'views' not in self.resources[rc]:
                    continue

                views = self.resources[rc]['views']

                if tail in views:
                    view = views[tail]
                    break

                elif '*' in views:
                    view = views['*']
                    break

        else:
            raise ViewNotResolved(request, resource, tail)

        if isinstance(view, SIMPLE_VIEWS_TYPES):
            return view
        else:
            return view(request, resource, tail)

    @resolver('resource', 'view')
    def bind_view(self, resource, view, tail=()):
        """ Bind view for resource.
        """
        if isinstance(tail, str) and tail != '*':
            tail = tuple(i for i in tail.split('/') if i)

        setup = self.resources.setdefault(resource, {'views': {}})
        setup.setdefault('views', {})[tail] = view

    def __repr__(self):
        return "<{}>".format(self.__class__.__name__)